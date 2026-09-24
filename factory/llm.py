"""Client du LLM local — un processus `llama-cli` par appel, qui se termine.

Règle 4 du projet : un seul modèle résident à la fois. Ce module n'ouvre jamais de serveur
persistant ; chaque `generate()` lance un sous-processus et l'attend. Le contexte est plafonné
à 8 k jetons (`CONTEXTE_MAX`) : au-delà, l'appel est refusé avant d'avoir chargé 6,17 Go.

Mesuré le 15/09/2026 sur cette machine (M2 16 Go, llama.cpp b10964) :
- génération ≈ 14 jetons/s sur Qwen3.5-9B Q4_K_M ;
- `--json-schema` / `-jf` **échoue** (« Failed to initialize samplers ») sur cette build, alors que
  `--grammar-file` fonctionne. D'où la conversion maison schéma → GBNF et le repli sans contrainte.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from factory.core.paths import dossier_workspace, racine_projet

logger = logging.getLogger(__name__)

#: Poids retenus par `outils/SELECTION.md` § 1 ; même chemin que `factory doctor`.
LLM_GGUF = (
    "models/llamacpp/models--bartowski--Qwen_Qwen3.5-9B-GGUF/snapshots/"
    "182be2fd6c7bc44887d88a91cb03ff009cc9f549/Qwen_Qwen3.5-9B-Q4_K_M.gguf"
)
LLM_REPO = "bartowski/Qwen_Qwen3.5-9B-GGUF"
LLM_QUANT = "Q4_K_M"
LLM_RUNTIME = "llama.cpp"

#: Plafond de contexte : 8 192 jetons, prompt + génération (ROADMAP étape 10).
CONTEXTE_MAX = 8192
#: Marge laissée au gabarit de conversation, jamais comptée dans l'estimation du prompt.
MARGE_GABARIT = 192
#: Estimation grossière du nombre de jetons — sert à REFUSER un prompt trop long, pas à mesurer.
CARACTERES_PAR_JETON = 3.3
#: Trois essais au maximum par appel JSON (prompt de l'étape 10).
ESSAIS_MAX = 3
TIMEOUT_DEFAUT_S = 1800


class ErreurLLM(RuntimeError):
    """Le sous-processus a échoué, dépassé son temps, ou rien produit d'exploitable."""


@dataclass
class ReponseLLM:
    """Ce qu'un appel a produit et ce qu'il a coûté. Aucune valeur n'est estimée ici."""

    texte: str
    secondes: float
    jetons_prompt: int | None = None
    jetons_generes: int | None = None
    debit_generation_tok_s: float | None = None
    tronque: bool = False
    contraint: bool = False
    code_retour: int = 0
    cache: bool = False

    def resume(self) -> str:
        """Une ligne pour le journal d'étape."""
        jetons = "non mesuré" if self.jetons_generes is None else f"{self.jetons_generes} jetons"
        debit = (
            "non mesuré" if self.debit_generation_tok_s is None
            else f"{self.debit_generation_tok_s:.1f} tok/s"
        )
        return (f"{self.secondes:.1f} s, {jetons}, {debit}"
                + (" [GBNF]" if self.contraint else "") + (" [cache]" if self.cache else ""))


@dataclass
class TraceLLM:
    """Trace d'une suite d'appels : ce que l'étape reporte au manifeste."""

    appels: list[ReponseLLM] = field(default_factory=list)

    @property
    def secondes(self) -> float:
        """Temps cumulé de tous les appels, relectures de cache comprises."""
        return sum(r.secondes for r in self.appels)

    @property
    def secondes_calculees(self) -> float:
        """Temps réellement passé à générer : les appels servis par le cache sont exclus."""
        return sum(r.secondes for r in self.appels if not r.cache)

    @property
    def appels_caches(self) -> int:
        """Nombre d'appels servis par le cache."""
        return sum(1 for r in self.appels if r.cache)

    @property
    def jetons_generes(self) -> int | None:
        """Jetons générés cumulés ; `None` si une seule mesure manque."""
        if any(r.jetons_generes is None for r in self.appels) or not self.appels:
            return None
        return sum(r.jetons_generes or 0 for r in self.appels)

    def ajouter(self, reponse: ReponseLLM) -> ReponseLLM:
        """Enregistre un appel et le renvoie."""
        self.appels.append(reponse)
        return reponse


# --------------------------------------------------------------------------------------
# Schéma JSON → GBNF
# --------------------------------------------------------------------------------------

_GBNF_SOCLE = """
ws ::= [ \\t\\n]*
chaine ::= "\\"" ( [^"\\\\\\x00-\\x1F] | "\\\\" ["\\\\/bfnrt] | "\\\\u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] )* "\\""
entier ::= "-"? ([0-9] | [1-9] [0-9]*)
nombre ::= entier ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
booleen ::= "true" | "false"
nul ::= "null"
"""


def _echapper_gbnf(valeur: str) -> str:
    """Littéral GBNF pour une chaîne JSON (les guillemets font partie du littéral)."""
    return json.dumps(json.dumps(valeur))[1:-1]


def schema_vers_gbnf(schema: dict[str, Any]) -> str:
    """Convertit un sous-ensemble de JSON Schema en grammaire GBNF pour llama.cpp.

    Sous-ensemble volontairement étroit — `object` à propriétés fixes, `array`, `string`
    (avec `enum`), `integer`, `number`, `boolean`, `null` — parce qu'une grammaire fausse
    fait échouer l'échantillonneur au lieu de dégrader la sortie. Tout le reste est rendu
    comme « n'importe quelle valeur JSON ».
    """
    regles: dict[str, str] = {}
    compteur = {"n": 0}

    def nom_libre(base: str) -> str:
        compteur["n"] += 1
        return f"{base}{compteur['n']}".replace("_", "-")

    def rendre(noeud: dict[str, Any], base: str) -> str:
        if not isinstance(noeud, dict):
            return "valeur"
        if "enum" in noeud:
            choix = " | ".join(f'"{_echapper_gbnf(str(v))}"' for v in noeud["enum"])
            nom = nom_libre(base)
            regles[nom] = choix
            return nom
        type_ = noeud.get("type")
        if isinstance(type_, list):  # ["string", "null"]
            sans_nul = [t for t in type_ if t != "null"]
            interne = rendre({**noeud, "type": sans_nul[0]}, base) if sans_nul else "nul"
            nom = nom_libre(base)
            regles[nom] = f"{interne} | nul"
            return nom
        if type_ == "string":
            return "chaine"
        if type_ == "integer":
            return "entier"
        if type_ == "number":
            return "nombre"
        if type_ == "boolean":
            return "booleen"
        if type_ == "null":
            return "nul"
        if type_ == "array":
            item = rendre(noeud.get("items", {}), f"{base}-item")
            mini = int(noeud.get("minItems", 0))
            nom = nom_libre(base)
            if mini >= 1:
                obligatoires = f"{item}" + f' ("," ws {item})' * (mini - 1)
                regles[nom] = f'"[" ws {obligatoires} ("," ws {item})* ws "]"'
            else:
                regles[nom] = f'"[" ws ({item} ("," ws {item})*)? ws "]"'
            return nom
        if type_ == "object":
            proprietes = noeud.get("properties") or {}
            if not proprietes:
                return "valeur"
            requis = list(noeud.get("required") or proprietes.keys())
            morceaux: list[str] = []
            for i, cle in enumerate(requis):
                if cle not in proprietes:
                    continue
                sous = rendre(proprietes[cle], f"{base}-{re.sub(r'[^a-z0-9]', '', cle.lower())}")
                virgule = '"," ws ' if i else ""
                morceaux.append(f'{virgule}"{_echapper_gbnf(cle)}" ws ":" ws {sous} ws')
            nom = nom_libre(base)
            regles[nom] = '"{" ws ' + " ".join(morceaux) + '"}"'
            return nom
        return "valeur"

    racine = rendre(schema, "n")
    corps = "\n".join(f"{nom} ::= {regle}" for nom, regle in regles.items())
    valeur = (
        "valeur ::= chaine | nombre | booleen | nul | tableau-libre | objet-libre\n"
        'tableau-libre ::= "[" ws (valeur ("," ws valeur)*)? ws "]"\n'
        'objet-libre ::= "{" ws (chaine ws ":" ws valeur ("," ws chaine ws ":" ws valeur)*)? ws "}"\n'
    )
    return f"root ::= ws {racine} ws\n{corps}\n{_GBNF_SOCLE}\n{valeur}"


# --------------------------------------------------------------------------------------
# Appel
# --------------------------------------------------------------------------------------

_RE_PROMPT = re.compile(r"prompt eval time\s*=\s*[\d.]+ ms\s*/\s*(\d+) tokens")
_RE_EVAL = re.compile(r"(?<!prompt )\beval time\s*=\s*[\d.]+ ms\s*/\s*(\d+) tokens\s*\(.*?([\d.]+) tokens per second")
_RE_TRONQUE = re.compile(r"truncated\s*=\s*([01])")
_RE_PERF = re.compile(r"\[\s*Prompt:.*?t/s\s*\|\s*Generation:.*?t/s\s*\]")
#: Fin de l'écho du prompt quand `llama-cli` l'a tronqué (voir `_nettoyer_sortie`).
_RE_ECHO_TRONQUE = re.compile(r"\.\.\.\s*\(truncated\)")
_ECHEC_GRAMMAIRE = "Failed to initialize samplers"


def estimer_jetons(texte: str) -> int:
    """Estimation grossière (≈ 3,3 caractères par jeton). Sert de garde, jamais de mesure."""
    return int(len(texte) / CARACTERES_PAR_JETON) + 1


def chemin_gguf(racine: Path | None = None) -> Path:
    """Chemin absolu des poids GGUF."""
    return (racine or racine_projet()) / LLM_GGUF


def _environnement(racine: Path) -> dict[str, str]:
    """Environnement du sous-processus : caches sous `models/`, aucun accès réseau utile."""
    env = dict(os.environ)
    env["LLAMA_CACHE"] = str(racine / "models" / "llamacpp")
    env["HF_HUB_OFFLINE"] = "1"
    return env


def _nettoyer_sortie(brut: str, prompt: str) -> str:
    """Retire la bannière, l'écho du prompt et la ligne de performance de `llama-cli`.

    `llama-cli` **tronque** son écho du prompt au-delà d'une certaine longueur et le clôt
    par « ... (truncated) » (mesuré le 18/09/2026 sur le juge de boucle de l'étape 16). Le
    marqueur des 120 derniers caractères du prompt est alors introuvable et l'écho restait
    collé à la réponse : tout exemple JSON du gabarit se retrouvait devant la génération.
    L'écho tronqué est donc coupé en premier, avant le marqueur exact.
    """
    texte = brut
    m_tronque = _RE_ECHO_TRONQUE.search(texte)
    if m_tronque is not None:
        texte = texte[m_tronque.end():]
    else:
        marqueur = prompt.strip()[-120:]
        if marqueur and marqueur in texte:
            texte = texte.split(marqueur, 1)[1]
        elif "\n> " in texte:
            texte = texte.rsplit("\n> ", 1)[1]
    texte = _RE_PERF.sub("", texte)
    return texte.replace("Exiting...", "").strip()


def _empreinte(
    prompt: str, system: str | None, max_tokens: int, temperature: float,
    json_schema: dict[str, Any] | None, seed: int | None, gguf: Path,
) -> str:
    """Empreinte d'un appel : mêmes entrées, même sortie — le modèle est appelé à graine fixe."""
    charge = json.dumps(
        [gguf.name, prompt, system, max_tokens, temperature, json_schema, seed],
        ensure_ascii=False, sort_keys=True,
    )
    return hashlib.sha256(charge.encode("utf-8")).hexdigest()


def _chemin_cache(empreinte: str, racine: Path) -> Path:
    return dossier_workspace(racine) / "cache" / "llm" / f"{empreinte}.json"


def _lire_cache(empreinte: str, racine: Path) -> ReponseLLM | None:
    """Relit une réponse déjà produite pour des entrées identiques.

    Un run de 28 segments demande une dizaine d'appels et une vingtaine de minutes : une erreur
    au dernier lot ne doit pas coûter la totalité. Le cache est désactivable par
    `FACTORY_LLM_NO_CACHE=1`.
    """
    if os.environ.get("FACTORY_LLM_NO_CACHE") == "1":
        return None
    chemin = _chemin_cache(empreinte, racine)
    if not chemin.exists():
        return None
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return ReponseLLM(**{**donnees, "cache": True})


def _ecrire_cache(empreinte: str, reponse: ReponseLLM, racine: Path) -> None:
    """Enregistre la réponse ; les temps conservés sont ceux de la génération d'origine."""
    if os.environ.get("FACTORY_LLM_NO_CACHE") == "1":
        return
    chemin = _chemin_cache(empreinte, racine)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    charge = {
        "texte": reponse.texte, "secondes": reponse.secondes,
        "jetons_prompt": reponse.jetons_prompt, "jetons_generes": reponse.jetons_generes,
        "debit_generation_tok_s": reponse.debit_generation_tok_s, "tronque": reponse.tronque,
        "contraint": reponse.contraint, "code_retour": reponse.code_retour,
    }
    chemin.write_text(json.dumps(charge, ensure_ascii=False), encoding="utf-8")


def _journaliser(entree: dict[str, Any], racine: Path) -> None:
    """Une ligne JSONL par appel dans `workspace/logs/llm.jsonl` (hors conversation)."""
    journal = dossier_workspace(racine) / "logs" / "llm.jsonl"
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8") as flux:
        flux.write(json.dumps(entree, ensure_ascii=False) + "\n")


def generate(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    json_schema: dict[str, Any] | None = None,
    seed: int | None = None,
    etiquette: str = "generate",
    timeout_s: int = TIMEOUT_DEFAUT_S,
    racine: Path | None = None,
) -> ReponseLLM:
    """Un appel, un sous-processus `llama-cli` qui se termine.

    `json_schema` contraint la génération par une grammaire GBNF dérivée du schéma. Si
    l'échantillonneur refuse la grammaire, l'appel est **rejoué sans contrainte** et
    `ReponseLLM.contraint` vaut `False` : c'est à l'appelant de valider la sortie.
    """
    racine = racine or racine_projet()
    gguf = chemin_gguf(racine)
    if not gguf.exists():
        raise ErreurLLM(f"poids GGUF absents : {gguf} (voir outils/MODELES.md)")

    empreinte = _empreinte(prompt, system, max_tokens, temperature, json_schema, seed, gguf)
    depuis_cache = _lire_cache(empreinte, racine)
    if depuis_cache is not None:
        _journaliser({"etiquette": etiquette, "secondes": 0.0, "cache": True,
                      "jetons_generes": depuis_cache.jetons_generes}, racine)
        return depuis_cache

    entree = estimer_jetons(prompt) + estimer_jetons(system or "") + MARGE_GABARIT
    if entree + max_tokens > CONTEXTE_MAX:
        raise ErreurLLM(
            f"contexte dépassé : ~{entree} jetons de prompt + {max_tokens} demandés "
            f"> {CONTEXTE_MAX} (estimation à {CARACTERES_PAR_JETON} car./jeton)"
        )

    with tempfile.TemporaryDirectory(prefix="factory-llm-") as tmp:
        dossier = Path(tmp)
        fichier_prompt = dossier / "prompt.txt"
        fichier_prompt.write_text(prompt, encoding="utf-8")
        cmd = [
            "llama-cli", "-m", str(gguf),
            "-c", str(CONTEXTE_MAX), "-n", str(max_tokens),
            "-st", "--no-warmup", "--no-display-prompt", "-rea", "off",
            "--temp", f"{temperature}", "-lv", "3",
            "-f", str(fichier_prompt),
        ]
        if seed is not None:
            cmd += ["-s", str(seed % (2**31))]
        if system:
            fichier_system = dossier / "system.txt"
            fichier_system.write_text(system, encoding="utf-8")
            cmd += ["-sysf", str(fichier_system)]
        contraint = False
        if json_schema is not None:
            fichier_gbnf = dossier / "schema.gbnf"
            fichier_gbnf.write_text(schema_vers_gbnf(json_schema), encoding="utf-8")
            cmd += ["--grammar-file", str(fichier_gbnf)]
            contraint = True

        reponse = _executer(cmd, prompt, contraint, timeout_s, racine, etiquette)
        if contraint and _ECHEC_GRAMMAIRE in reponse.texte:
            logger.warning("grammaire GBNF refusée par l'échantillonneur : repli sans contrainte")
            reponse = _executer(
                [a for a in cmd if a not in ("--grammar-file", str(dossier / "schema.gbnf"))],
                prompt, False, timeout_s, racine, f"{etiquette}:repli",
            )
    if reponse.code_retour == 0 and reponse.texte:
        _ecrire_cache(empreinte, reponse, racine)
    return reponse


def _executer(
    cmd: list[str], prompt: str, contraint: bool, timeout_s: int, racine: Path, etiquette: str
) -> ReponseLLM:
    """Lance `llama-cli`, mesure, journalise. Le message exact de l'outil n'est jamais reformulé."""
    t0 = time.perf_counter()
    try:
        # Sortie capturée en octets : l'animation de chargement de `llama-cli` entrelace des
        # caractères de contrôle qui coupent un caractère UTF-8 en deux (mesuré le 15/09/2026).
        p = subprocess.run(
            cmd, capture_output=True, timeout=timeout_s, env=_environnement(racine)
        )
    except subprocess.TimeoutExpired as exc:
        raise ErreurLLM(f"llama-cli a dépassé {timeout_s} s ({etiquette})") from exc
    secondes = time.perf_counter() - t0

    sortie = (p.stdout or b"").decode("utf-8", errors="replace")
    journal_erreur = (p.stderr or b"").decode("utf-8", errors="replace")
    m_prompt = _RE_PROMPT.search(journal_erreur)
    m_eval = _RE_EVAL.search(journal_erreur)
    tronque = any(v == "1" for v in _RE_TRONQUE.findall(journal_erreur))
    texte = _nettoyer_sortie(sortie, prompt)

    reponse = ReponseLLM(
        texte=texte,
        secondes=secondes,
        jetons_prompt=int(m_prompt.group(1)) if m_prompt else None,
        jetons_generes=int(m_eval.group(1)) if m_eval else None,
        debit_generation_tok_s=float(m_eval.group(2)) if m_eval else None,
        tronque=tronque,
        contraint=contraint,
        code_retour=p.returncode,
    )
    _journaliser(
        {
            "etiquette": etiquette,
            "secondes": round(secondes, 2),
            "jetons_prompt": reponse.jetons_prompt,
            "jetons_generes": reponse.jetons_generes,
            "tok_s": reponse.debit_generation_tok_s,
            "contraint": contraint,
            "tronque": tronque,
            "code": p.returncode,
            "caracteres": len(texte),
        },
        racine,
    )
    if p.returncode != 0 and not texte:
        raise ErreurLLM(f"llama-cli code {p.returncode} ({etiquette}) : {journal_erreur[-300:]}")
    return reponse


# --------------------------------------------------------------------------------------
# Réparation JSON
# --------------------------------------------------------------------------------------

def _objets_equilibres(texte: str) -> list[str]:
    """Tous les objets à accolades équilibrées du texte, dans l'ordre d'apparition."""
    trouves: list[str] = []
    debut = texte.find("{")
    while debut != -1:
        profondeur, dans_chaine, echappe = 0, False, False
        for i in range(debut, len(texte)):
            car = texte[i]
            if dans_chaine:
                if echappe:
                    echappe = False
                elif car == "\\":
                    echappe = True
                elif car == '"':
                    dans_chaine = False
                continue
            if car == '"':
                dans_chaine = True
            elif car == "{":
                profondeur += 1
            elif car == "}":
                profondeur -= 1
                if profondeur == 0:
                    trouves.append(texte[debut : i + 1])
                    break
        debut = texte.find("{", debut + 1)
    return trouves


def extraire_objet(texte: str) -> str | None:
    """Premier objet JSON du texte **qui se parse réellement**.

    L'équilibre des accolades ne suffit pas : un gabarit de prompt comme
    `{"answers": true or false, "why": "..."}` est équilibré et ne se parse pas. Rendre le
    premier objet équilibré faisait alors échouer les trois essais sur l'exemple du prompt
    au lieu de la génération (étape 16, 18/09/2026). À défaut de candidat valide, le premier
    est rendu tel quel : c'est son message d'erreur exact que `generate_json` rapporte.
    """
    candidats = _objets_equilibres(texte)
    for candidat in candidats:
        try:
            json.loads(candidat)
        except json.JSONDecodeError:
            continue
        return candidat
    return candidats[0] if candidats else None


def generate_json(
    prompt: str,
    system: str | None = None,
    modele: type[BaseModel] | None = None,
    json_schema: dict[str, Any] | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.7,
    seed: int | None = None,
    etiquette: str = "json",
    trace: TraceLLM | None = None,
    racine: Path | None = None,
    timeout_s: int = TIMEOUT_DEFAUT_S,
) -> tuple[Any, ReponseLLM]:
    """Génère un objet JSON valide : grammaire, puis extraction, puis relance avec l'erreur.

    Trois essais au maximum. À chaque échec, le message exact de `json` ou de pydantic est
    renvoyé au modèle — c'est ce qui répare le mieux un 9B quantifié.
    """
    dernier_probleme = ""
    prompt_courant = prompt
    for essai in range(1, ESSAIS_MAX + 1):
        reponse = generate(
            prompt_courant, system=system, max_tokens=max_tokens, temperature=temperature,
            json_schema=json_schema, seed=None if seed is None else seed + essai,
            etiquette=f"{etiquette}#{essai}", racine=racine, timeout_s=timeout_s,
        )
        if trace is not None:
            trace.ajouter(reponse)
        coupee = reponse.jetons_generes is not None and reponse.jetons_generes >= max_tokens
        brut = None if coupee else extraire_objet(reponse.texte)
        if coupee:
            # Une réponse coupée au plafond laisse un objet racine déséquilibré : l'extraction
            # y répondrait par un sous-objet, donc par un résultat faux. On relance.
            dernier_probleme = (
                f"réponse coupée au plafond de {max_tokens} jetons : produis moins d'éléments "
                "et des phrases plus courtes"
            )
        elif brut is None:
            dernier_probleme = "aucun objet JSON dans la réponse"
        else:
            try:
                donnees = json.loads(brut)
            except json.JSONDecodeError as exc:
                dernier_probleme = f"JSON invalide : {exc}"
            else:
                if modele is None:
                    absentes = [
                        c for c in ((json_schema or {}).get("required") or [])
                        if c not in donnees
                    ]
                    if absentes:
                        dernier_probleme = f"clés absentes de l'objet : {absentes}"
                    else:
                        return donnees, reponse
                else:
                    try:
                        return modele.model_validate(donnees), reponse
                    except ValidationError as exc:
                        dernier_probleme = "; ".join(
                            f"{'.'.join(str(p) for p in e['loc'])} : {e['msg']}"
                            for e in exc.errors()[:6]
                        )
        logger.warning("%s essai %d refusé — %s", etiquette, essai, dernier_probleme)
        prompt_courant = (
            f"{prompt}\n\n---\nTa réponse précédente a été refusée : {dernier_probleme}\n"
            "Renvoie uniquement l'objet JSON corrigé, sans commentaire ni texte autour."
        )
    raise ErreurLLM(f"{etiquette} : {ESSAIS_MAX} essais, dernier refus — {dernier_probleme}")
