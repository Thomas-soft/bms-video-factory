"""`factory script` — écriture du script structuré par le LLM local.

**Comment la durée cible est tenue.** `estimated_duration_s = mots / (mots_par_minute / 60)` :
la seule variable est le nombre de mots. Le programme ne demande donc pas « un script de
11 minutes » — un 9B quantifié n'a aucune idée de ce que cela fait — mais **un budget de mots
par segment**, calculé à partir de la cible de niche. Le squelette (rôles, boucles ouvertes,
ruptures, budgets) est construit par le code ; le LLM ne remplit que le texte.

**Pourquoi la génération est découpée.** Le contexte est plafonné à 8 k jetons et la cible de
`science_pop` vaut ~1 460 mots : un script entier en un seul objet JSON ne tient pas dans la
fenêtre, et un 9B perd la structure bien avant. La génération est donc : un plan, puis
l'accroche, puis la narration par lots de quelques segments. Chaque appel est petit, contraint
par une grammaire GBNF, validé par pydantic, et relancé au besoin — c'est la divergence assumée
avec le prompt de l'étape 10, qui décrivait un appel unique.

**Nombre de segments.** Un segment par intervalle de rupture, avec
`N = 4 × rythme_coupe_s.cible_montage` : c'est ce qui permet à chaque segment de porter sa
rupture, le modèle de données n'en acceptant qu'une par segment.
"""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factory import llm
from factory.core import config as config_module
from factory.core import db, referentiel, runs
from factory.core.models import (
    Hook,
    Interrupt,
    LignesDivulgation,
    Research,
    Script,
    ScriptSegment,
    SignatureEditoriale,
)
from factory.core.paths import RunPaths, racine_projet

#: Multiplicateur du rythme de coupe qui donne la cadence des ruptures (prompt étape 10).
FACTEUR_RUPTURE = 4
#: Bornes du nombre de segments : en deçà le script n'a plus de structure, au-delà il se hache.
SEGMENTS_MIN, SEGMENTS_MAX = 8, 32
#: Taille d'un lot d'écriture — compromis entre nombre d'appels et tenue du contexte.
LOT = 4
#: Corrections de durée autorisées (prompt étape 10).
CORRECTIONS_MAX = 2
MOTS_ECRAN_MAX = 6
TYPES_RUPTURE = ["question", "chiffre", "silence", "changement_de_plan"]


@dataclass
class ResultatScript:
    """Ce que `script` a produit, et ce qu'il a coûté."""

    script: Script
    hook_type: str
    hook_part: float
    mots_cibles: int
    secondes: float
    corrections: int
    alertes: list[str] = field(default_factory=list)
    trace: llm.TraceLLM = field(default_factory=llm.TraceLLM)


# --------------------------------------------------------------------------------------
# Gabarits de prompt
# --------------------------------------------------------------------------------------

def charger_gabarits(lang: str, racine: Path | None = None) -> dict[str, str]:
    """Sections `##` de `factory/prompts/script_<lang>.md`, repli sur l'anglais."""
    dossier = (racine or racine_projet()) / "factory" / "prompts"
    chemin = dossier / f"script_{lang}.md"
    if not chemin.exists():
        chemin = dossier / "script_en.md"
    sections: dict[str, str] = {}
    courante: str | None = None
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.startswith("## "):
            courante = ligne[3:].strip()
            sections[courante] = ""
        elif courante:
            sections[courante] += ligne + "\n"
    return {cle: valeur.strip() for cle, valeur in sections.items()}


def remplir(gabarit: str, valeurs: dict[str, Any], strict: bool = True) -> str:
    """Substitue `{{clef}}` — pas `str.format`, qui butterait sur les accolades du JSON.

    `strict=False` sert au gabarit de correction, rempli en deux temps : les valeurs communes
    d'abord, puis la liste des segments, lot par lot.
    """
    texte = gabarit
    for cle, valeur in valeurs.items():
        texte = texte.replace("{{" + cle + "}}", str(valeur))
    restants = re.findall(r"\{\{(\w+)\}\}", texte)
    if restants and strict:
        raise KeyError(f"gabarit : valeurs manquantes {sorted(set(restants))}")
    return texte


# --------------------------------------------------------------------------------------
# Squelette : rôles, boucles ouvertes, ruptures, budgets de mots
# --------------------------------------------------------------------------------------

@dataclass
class Case:
    """Un emplacement de segment, décidé par le code avant tout appel au LLM."""

    index: int
    role: str
    open_loop: str
    mots: int
    interrupt: Interrupt | None = None

    @property
    def identifiant(self) -> str:
        """`seg_00`, `seg_01`, …"""
        return f"seg_{self.index:02d}"


def construire_squelette(
    n_segments: int, mots_cibles: int, mots_hook_max: int, avec_sponsor: bool, seed: int,
    duree_cible_s: float, intervalle_rupture_s: float,
) -> list[Case]:
    """Rôles, boucles ouvertes, ruptures et budget de mots — avant le premier appel au LLM.

    Boucles : l'accroche plante la première, le segment suivant plante la seconde
    (« plantée avant le 2e segment »), et les deux sont payées avant la conclusion.
    """
    roles: list[str] = ["hook", "contexte"]
    dernier = n_segments - 1
    position_sponsor = 3 if avec_sponsor else None
    for i in range(2, n_segments):
        if i == position_sponsor:
            roles.append("sponsor")
        elif i == dernier:
            roles.append("conclusion")
        elif i == dernier - 1:
            roles.append("cta")
        else:
            roles.append("point")

    boucles = ["none"] * n_segments
    boucles[0] = "plant"
    boucles[1] = "plant"
    index_payoffs = [max(2, int(n_segments * 0.55)), max(3, dernier - 2)]
    for index in index_payoffs:
        while index < n_segments and (roles[index] in {"sponsor", "cta", "conclusion"}
                                      or boucles[index] == "payoff"):
            index -= 1
        if index >= 2:
            boucles[index] = "payoff"

    cases: list[Case] = []
    mots_hook = min(mots_hook_max, max(20, mots_cibles // n_segments))
    reste = max(1, mots_cibles - mots_hook)
    autres = n_segments - 1
    for i, role in enumerate(roles):
        mots = mots_hook if i == 0 else round(reste / autres)
        cases.append(Case(index=i, role=role, open_loop=boucles[i], mots=mots))

    # Une rupture par segment, calée sur la cadence N = 4 × rythme de coupe.
    horloge = 0.0
    import random as _random
    alea = _random.Random(seed)
    for case in cases:
        duree_segment = duree_cible_s * case.mots / max(1, mots_cibles)
        if duree_segment >= intervalle_rupture_s * 0.5 and case.role != "hook":
            case.interrupt = Interrupt(
                type=alea.choice(TYPES_RUPTURE),
                at_s_relative=round(min(duree_segment * 0.5, intervalle_rupture_s / 2), 1),
            )
        horloge += duree_segment
    return cases


# --------------------------------------------------------------------------------------
# Schémas des appels
# --------------------------------------------------------------------------------------

SCHEMA_PLAN = {
    "type": "object",
    "properties": {"segments": {"type": "array", "minItems": 2, "items": {
        "type": "object", "properties": {
            "id": {"type": "string"}, "beat": {"type": "string"},
            "on_screen_text": {"type": "string"}, "visual_intent": {"type": "string"},
            "sources": {"type": "array", "items": {"type": "string"}}},
        "required": ["id", "beat", "on_screen_text", "visual_intent", "sources"]}}},
    "required": ["segments"],
}

SCHEMA_HOOK = {
    "type": "object",
    "properties": {"text": {"type": "string"}, "on_screen_text": {"type": "string"},
                   "visual_intent": {"type": "string"}},
    "required": ["text", "on_screen_text", "visual_intent"],
}

SCHEMA_NARRATION = {
    "type": "object",
    "properties": {"segments": {"type": "array", "minItems": 1, "items": {
        "type": "object", "properties": {"id": {"type": "string"},
                                         "narration": {"type": "string"}},
        "required": ["id", "narration"]}}},
    "required": ["segments"],
}


def _mots(texte: str) -> int:
    return len(texte.split())


#: Au-delà de ce dépassement du budget, un segment est retaillé par phrases entières.
MARGE_HAUTE = 1.2
#: Bornes du facteur de correction : sans elles, deux passes suffisent à faire exploser
#: les budgets et le modèle bute sur le plafond de jetons (mesuré le 15/09/2026).
FACTEUR_MIN, FACTEUR_MAX = 0.6, 1.6


def _phrases(texte: str) -> list[str]:
    return [p for p in re.split(r"(?<=[.!?…])\s+", texte.strip()) if p]


def _retailler(narration: str, budget: int) -> str:
    """Ramène un segment à son budget, **par phrases entières**, sans appeler le LLM.

    Mesuré le 15/09/2026 : sur certains lots, le 9B écrit jusqu'à 3 fois le nombre de mots
    demandé. Raccourcir est une opération déterministe ; seul l'allongement a besoin du modèle.
    Une phrase n'est jamais coupée en son milieu, et la première est toujours conservée.
    """
    if len(narration.split()) <= budget * MARGE_HAUTE:
        return narration
    garde: list[str] = []
    for phrase in _phrases(narration):
        if garde and len(" ".join([*garde, phrase]).split()) > budget * 1.1:
            break
        garde.append(phrase)
    return " ".join(garde) if garde else narration


def _retaillables(cases: list[Case]) -> list[Case]:
    """Segments qu'on peut raccourcir sans casser leur fonction.

    Une boucle `plant` se termine sur une promesse et un `payoff` y répond dès sa première
    phrase : les tailler par la fin détruirait justement ce que l'étape 16 vérifie. Idem pour
    l'appel à l'action, la conclusion et le segment sponsorisé, dont la phrase de divulgation
    est contractuelle.
    """
    return [c for c in cases
            if c.role in {"point", "contexte"} and c.open_loop == "none"]


def _normaliser_capitales(texte: str) -> str:
    """Rend à un texte parlé une casse de phrase.

    Mesuré le 15/09/2026 : le modèle a rendu l'accroche française entièrement en capitales,
    parce que la consigne voisine demande des capitales pour le **texte à l'écran**. Or
    `narration` est le seul texte envoyé au TTS (INTERFACES § script.json) : des capitales y
    font épeler des sigles. La casse est donc remise ici, pas redemandée au modèle.
    """
    lettres = [c for c in texte if c.isalpha()]
    if not lettres or sum(1 for c in lettres if c.isupper()) / len(lettres) < 0.7:
        return texte
    phrases = [p for p in re.split(r"(?<=[.!?…])\s+", texte.lower()) if p]
    return " ".join(p[0].upper() + p[1:] if p else p for p in phrases)


def _texte_ecran(brut: str | None) -> str | None:
    """Plafonne le texte à l'écran à 6 mots et retire la ponctuation finale."""
    if not brut:
        return None
    propre = re.sub(r"\s+", " ", brut).strip().strip(".!?:;,")
    if not propre:
        return None
    return " ".join(propre.split()[:MOTS_ECRAN_MAX]).upper()


# --------------------------------------------------------------------------------------
# Étape
# --------------------------------------------------------------------------------------

def executer(video_id: str, racine: Path | None = None) -> ResultatScript:
    """Tire le hook, écrit le plan, l'accroche puis la narration, et cale la durée."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.research.exists():
        raise FileNotFoundError(f"research.json absent : lance `factory research --run {video_id}`")
    recherche = Research.model_validate_json(chemins.research.read_text(encoding="utf-8"))

    mpm = referentiel.mots_par_minute(spec.niche, racine)
    mots_cibles = int(round(spec.target_duration_s * mpm / 60))
    tolerance = float(cfg.niches[spec.niche].duree_s.tolerance)
    intervalle = FACTEUR_RUPTURE * spec.cut_rhythm_target_s
    n_segments = max(SEGMENTS_MIN, min(SEGMENTS_MAX, round(spec.target_duration_s / intervalle)))
    mots_hook_max = referentiel.longueur_hook_max(spec.niche, racine)

    hook_type, hook_part = referentiel.tirer_type_hook(spec.niche, spec.seed, racine)
    taxonomie = referentiel.taxonomie_hooks(racine)[hook_type]

    produit = cfg.products.get(spec.product_id) if spec.product_id else None
    cases = construire_squelette(
        n_segments, mots_cibles, mots_hook_max, produit is not None, spec.seed,
        float(spec.target_duration_s), intervalle,
    )
    gabarits = charger_gabarits(spec.lang, racine)
    systeme = gabarits["systeme"]
    trace = llm.TraceLLM()

    faits_txt = "\n".join(
        f"- {f.id} : {f.claim}" + (f" [{f.value} {f.unit or ''}]".rstrip() if f.value else "")
        for f in recherche.facts
    )
    faits_par_id = {f.id: f.claim for f in recherche.facts}
    from factory.steps.research import persona as _persona
    commun = {
        "sujet": spec.topic.sujet, "angle": recherche.angle,
        "elements_proprietaires": " ; ".join(recherche.elements_proprietaires) or "—",
        "persona": _persona(channel, cfg), "faits": faits_txt,
        # Formulée comme une interdiction et non comme une liste de jetons : à l'itération 1
        # des prompts, le modèle recopiait « bust_only » tel quel en tête de chaque intention.
        "cadrage": (
            "La charte de la chaîne interdit les plans de personnage en pied et en mouvement ; "
            f"privilégie {', '.join(channel.charte.framing.prefer)}."
        ),
        "mots_cibles": mots_cibles, "duree_cible_s": spec.target_duration_s,
        "mots_par_minute": mpm,
    }

    # 1 — plan.
    roles_txt = "\n".join(
        f"  {c.identifiant} : rôle {c.role}, boucle {c.open_loop}, {c.mots} mots"
        for c in cases
    )
    plan_donnees, _ = llm.generate_json(
        remplir(gabarits["plan"], {**commun, "n_segments": n_segments,
                                  "dernier_segment": n_segments - 1, "roles": "\n" + roles_txt}),
        system=systeme, json_schema=SCHEMA_PLAN, max_tokens=2800, temperature=0.6,
        seed=spec.seed % 100000, etiquette="script:plan", trace=trace, racine=racine,
    )
    plan: dict[str, dict[str, Any]] = {}
    for entree in plan_donnees["segments"]:
        identifiant = str(entree.get("id", "")).strip()
        if not re.fullmatch(r"seg_\d{2,3}", identifiant):
            chiffres = re.findall(r"\d+", identifiant)
            if not chiffres:
                continue
            identifiant = f"seg_{int(chiffres[-1]):02d}"
        plan[identifiant] = entree
    manquants = [c.identifiant for c in cases if c.identifiant not in plan]
    if manquants:
        alertes.append(f"plan : {len(manquants)} segment(s) non planifiés, repli sur le rôle "
                       f"({', '.join(manquants[:5])}{'…' if len(manquants) > 5 else ''})")

    # 2 — accroche du type tiré.
    exemples = taxonomie.get("exemples") or []
    exemple = next((e["verbatim"] for e in exemples if e.get("langue") == spec.lang),
                   exemples[0]["verbatim"] if exemples else "—")
    hook_donnees, _ = llm.generate_json(
        remplir(gabarits["hook"], {**commun, "hook_type": hook_type,
                                  "hook_definition": taxonomie.get("definition", ""),
                                  "hook_regles": "\n".join(f"- {r}" for r in taxonomie.get("regles", [])),
                                  "hook_exemple": exemple[:300], "hook_mots_max": mots_hook_max}),
        system=systeme, json_schema=SCHEMA_HOOK, max_tokens=500, temperature=0.8,
        seed=spec.seed % 100000, etiquette="script:hook", trace=trace, racine=racine,
    )
    hook_text = _normaliser_capitales(re.sub(r"\s+", " ", str(hook_donnees["text"])).strip())
    if _mots(hook_text) > mots_hook_max:
        alertes.append(
            f"hook : {_mots(hook_text)} mots pour un plafond de {mots_hook_max} (médiane de "
            f"niche) — tronqué à la phrase"
        )
        phrases, garde = re.split(r"(?<=[.!?])\s+", hook_text), []
        for phrase in phrases:
            if _mots(" ".join(garde + [phrase])) > mots_hook_max and garde:
                break
            garde.append(phrase)
        hook_text = " ".join(garde) or " ".join(hook_text.split()[:mots_hook_max])

    # 3 — narration, par lots.
    plan_resume = "\n".join(
        f"  {c.identifiant} ({c.role}, {c.open_loop}) : "
        f"{plan.get(c.identifiant, {}).get('beat', '—')}"
        for c in cases
    )
    narrations: dict[str, str] = {}
    a_ecrire = [c for c in cases if c.role != "hook"]
    _ecrire_lots(a_ecrire, {c.identifiant: c.mots for c in a_ecrire}, narrations, plan, cases,
                 gabarits, commun, systeme, plan_resume, hook_text, produit, cfg, channel,
                 spec, trace, racine, "script:narration", faits_par_id)

    # 4 — calage de la durée. Raccourcir se fait en code ; seul l'allongement passe par le LLM.
    def _total() -> int:
        return _mots(hook_text) + sum(_mots(t) for t in narrations.values())

    retaillables = _retaillables(cases)
    for case in retaillables:
        narrations[case.identifiant] = _retailler(narrations.get(case.identifiant, ""), case.mots)
    depassement = _total() - mots_cibles
    if depassement > mots_cibles * tolerance and retaillables:
        # Encore trop long après la retaille au budget : on resserre les budgets eux-mêmes.
        mots_retaillables = sum(_mots(narrations[c.identifiant]) for c in retaillables)
        facteur = max(FACTEUR_MIN,
                      (mots_retaillables - depassement) / max(1, mots_retaillables))
        for case in retaillables:
            narrations[case.identifiant] = _retailler(
                narrations[case.identifiant], max(20, round(case.mots * facteur)))
        alertes.append(
            f"durée : script retaillé en code (facteur {facteur:.2f}) — le modèle a écrit "
            f"{depassement + mots_cibles} mots pour {mots_cibles} demandés"
        )

    corrections = 0
    for _ in range(CORRECTIONS_MAX):
        total = _total()
        ecart = (total - mots_cibles) / mots_cibles
        if ecart >= -tolerance:
            break  # trop long est déjà traité par la retaille ; ici on ne gère que trop court
        corrections += 1
        ajustables = [c for c in cases if c.role in {"contexte", "point"}]
        if not ajustables:
            break
        mots_ajustables = sum(_mots(narrations.get(c.identifiant, "")) for c in ajustables)
        manque = mots_cibles - total
        facteur = min(FACTEUR_MAX,
                      (mots_ajustables + manque) / max(1, mots_ajustables))
        budgets = {
            c.identifiant: max(25, round(_mots(narrations.get(c.identifiant, "")) * facteur))
            for c in ajustables
        }
        sens = ("l'allonger" if manque > 0 else "le raccourcir") if spec.lang == "fr" \
            else ("expanded" if manque > 0 else "shortened")
        supplement = remplir(gabarits["correction"], {
            **commun, "mots_obtenus": total, "ecart_pct": round(ecart * 100, 1),
            "tolerance_pct": round(tolerance * 100), "sens": sens, "hook_text": hook_text,
        }, strict=False)  # `segments_a_ecrire`, `deja_dit` et `phrase_precedente` : par lot  # `segments_a_ecrire` est rempli lot par lot par `_ecrire_lots`
        _ecrire_lots(ajustables, budgets, narrations, plan, cases, gabarits, commun, systeme,
                     plan_resume, hook_text, produit, cfg, channel, spec, trace, racine,
                     f"script:correction{corrections}", faits_par_id,
                     gabarit_force=supplement)
        for case in retaillables:
            narrations[case.identifiant] = _retailler(
                narrations.get(case.identifiant, ""), budgets.get(case.identifiant, case.mots))

    # 5 — assemblage et validation.
    segments: list[ScriptSegment] = []
    for case in cases:
        entree = plan.get(case.identifiant, {})
        if case.role == "hook":
            narration = hook_text
            ecran = _texte_ecran(hook_donnees.get("on_screen_text"))
            visuel = str(hook_donnees.get("visual_intent") or "").strip()
        else:
            narration = narrations.get(case.identifiant, "").strip()
            ecran = _texte_ecran(entree.get("on_screen_text"))
            visuel = str(entree.get("visual_intent") or "").strip()
        if not narration:
            raise RuntimeError(f"{case.identifiant} : narration vide après génération")
        if not visuel:
            visuel = ("Plan serré sur un objet du sujet, sans personnage."
                      if spec.lang == "fr" else "Close shot on an object of the topic, no person.")
            alertes.append(f"{case.identifiant} : intention visuelle absente, repli générique")
        sources = [s for s in (entree.get("sources") or [])
                   if isinstance(s, str) and s in {f.id for f in recherche.facts}]
        segments.append(ScriptSegment(
            id=case.identifiant, role=case.role, narration=narration, on_screen_text=ecran,
            visual_intent=visuel[:500], open_loop=case.open_loop, interrupt=case.interrupt,
            sources=sources,
            disclosure_spoken=(case.role == "sponsor"),
        ))

    lignes = _lignes_divulgation(produit, cfg, spec.lang) if produit is not None else None

    mots_total = sum(s.word_count for s in segments)
    duree = mots_total / (mpm / 60)
    script = Script(
        lang=spec.lang,
        hook=Hook(type=hook_type, text=hook_text),
        segments=segments,
        editorial_signature=SignatureEditoriale(
            angle=recherche.angle_signature,
            elements_proprietaires=recherche.elements_proprietaires or [recherche.angle],
        ),
        word_count=mots_total, estimated_duration_s=round(duree, 1), disclosure_lines=lignes,
    )
    runs.ecrire_json(chemins.script, script)

    ecart_final = (duree - spec.target_duration_s) / spec.target_duration_s
    if abs(ecart_final) > tolerance:
        alertes.append(
            f"durée : {duree:.0f} s pour une cible de {spec.target_duration_s} s "
            f"({ecart_final * 100:+.1f} %, tolérance ± {tolerance * 100:.0f} %) après "
            f"{corrections} correction(s)"
        )
    contenu = [s for s in segments if s.role in {"point", "contexte"}]
    if contenu and len(recherche.facts) / len(contenu) < 0.5:
        alertes.append(
            f"densité : {len(recherche.facts)} faits pour {len(contenu)} segments de contenu "
            f"({len(recherche.facts) / len(contenu):.2f} fait/segment). Chaque fait est resservi "
            "environ " + f"{len(contenu) / max(1, len(recherche.facts)):.1f} fois : c'est la "
            "cause mesurée des répétitions. À traiter à l'étape 16 (plus de faits, ou moins de "
            "segments)."
        )
    pauvres = [s.id for s in segments if s.role == "point" and not s.sources]
    if pauvres:
        alertes.append(f"{len(pauvres)} segment(s) `point` sans fait cité : {', '.join(pauvres[:5])}"
                       " — rejetés par l'étape 16")

    secondes = time.perf_counter() - t0
    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.hook_type = hook_type
    manifest.decisions.duration_s = round(duree, 1)
    manifest.decisions.density_facts_per_min = round(
        len({s for seg in segments for s in seg.sources}) / max(1e-9, duree / 60), 2)
    manifest.decisions.open_loops.planted = sum(1 for s in segments if s.open_loop == "plant")
    manifest.decisions.open_loops.paid = sum(1 for s in segments if s.open_loop == "payoff")
    horloge, positions = 0.0, []
    ruptures: list[Interrupt] = []
    for segment in segments:
        duree_segment = segment.word_count / (mpm / 60)
        if segment.open_loop == "plant":
            positions.append(round(horloge, 1))
        if segment.interrupt:
            ruptures.append(Interrupt(type=segment.interrupt.type,
                                      at_s_relative=round(horloge + segment.interrupt.at_s_relative, 1)))
        horloge += duree_segment
    manifest.decisions.open_loops.positions_s = positions
    manifest.decisions.interrupts = ruptures
    manifest.execution.timings["script"] = round(secondes, 2)
    manifest.execution.timings["script_llm"] = round(trace.secondes, 2)
    manifest.execution.timings["script_appels"] = len(trace.appels)
    manifest.execution.run_state = "awaiting_review"
    if not any(m.brique == "llm" for m in manifest.execution.modeles):
        from factory.core.models import ModeleUtilise
        manifest.execution.modeles.append(ModeleUtilise(
            brique="llm", repo=llm.LLM_REPO, quantization=llm.LLM_QUANT,
            runtime=llm.LLM_RUNTIME, runtime_version=_version_llama(),
        ))
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()
    return ResultatScript(script, hook_type, hook_part, mots_cibles, secondes, corrections,
                          alertes, trace)


def _lignes_divulgation(produit: Any, cfg: Any, lang: str) -> LignesDivulgation:
    """Les trois lignes de divulgation, dans l'ordre de priorité de `CONFORMITE` § 3.

    La surcharge du produit prime ; à défaut, la ligne vient de `config/languages/<lang>.yaml`,
    **jamais du code** : les mentions Amazon, Impact et Awin sont contractuelles et ne se
    reformulent pas. La mention à l'écran reste la mention générique de la langue (loi 2023-451),
    même quand le réseau impose sa propre formule à l'oral.
    """
    surcharge = produit.disclosure_override.get(lang)
    if surcharge is not None:
        return surcharge
    disclosure = cfg.languages[lang].disclosure
    ligne = disclosure.pour_reseau(produit.network)
    # Les listes fermées d'Impact et d'Awin sont des **hashtags** (`#ad`, `#PaidAd`) : elles ne
    # se prononcent pas. La ligne orale retombe donc sur la mention générique de la langue
    # (« Publicité », loi 2023-451), qui est une phrase. Retirer le croisillon reviendrait à
    # réécrire une mention contractuelle : c'est une décision d'Alek, pas du code
    # (SUIVI.md § 1, action n° 12).
    parlee = ligne if not ligne.lstrip().startswith("#") else disclosure.overlay_generic
    return LignesDivulgation(
        description_line=ligne,
        overlay_text=disclosure.overlay_generic,
        spoken_line=parlee,
    )


def _version_llama() -> str:
    """Version de `llama-cli`, telle qu'elle se présente. Jamais devinée."""
    import subprocess
    try:
        p = subprocess.run(["llama-cli", "--version"], capture_output=True, text=True, timeout=20)
        blob = (p.stdout + p.stderr).strip().splitlines()
        return next((l.split()[-1] for l in blob if "version" in l.lower()), blob[0] if blob else "?")
    except (OSError, subprocess.SubprocessError):
        return "non mesuré"


def _ecrire_lots(
    a_ecrire: list[Case], budgets: dict[str, int], narrations: dict[str, str],
    plan: dict[str, dict[str, Any]], cases: list[Case], gabarits: dict[str, str],
    commun: dict[str, Any], systeme: str, plan_resume: str, hook_text: str, produit: Any,
    cfg: Any, channel: Any, spec: Any, trace: llm.TraceLLM, racine: Path | None,
    etiquette: str, faits_par_id: dict[str, str], gabarit_force: str | None = None,
) -> None:
    """Écrit la narration par lots de `LOT` segments ; chaque lot est un appel qui se termine."""
    gabarit = gabarit_force or gabarits["narration"]
    for debut in range(0, len(a_ecrire), LOT):
        lot = a_ecrire[debut : debut + LOT]
        lignes = []
        for case in lot:
            entree = plan.get(case.identifiant, {})
            consigne = (f"- {case.identifiant} — rôle {case.role}, boucle {case.open_loop}, "
                        f"{budgets[case.identifiant]} mots. Sujet du segment : "
                        f"{entree.get('beat', case.role)}. "
                        f"Faits à citer : {', '.join(entree.get('sources') or []) or 'aucun imposé'}.")
            if case.role == "sponsor" and produit is not None:
                consigne += "\n" + remplir(gabarits["sponsor"], {
                    "produit": produit.name,
                    "phrase_divulgation": _lignes_divulgation(produit, cfg, spec.lang).spoken_line,
                })
            lignes.append(consigne)
        # Mémoire entre les lots : sans elle, chaque appel redonne les mêmes chiffres
        # (mesuré le 15/09/2026 : un même volume répété dans 8 segments sur 28).
        precedents = [c for c in cases if c.index < lot[0].index]
        deja_ids: list[str] = []
        for case in precedents:
            for identifiant in plan.get(case.identifiant, {}).get("sources") or []:
                if identifiant not in deja_ids:
                    deja_ids.append(str(identifiant))
        deja_dit = "\n".join(f"- {i} : {faits_par_id.get(i, '')}" for i in deja_ids) or "rien encore"
        precedent = next((narrations.get(c.identifiant, "") for c in reversed(precedents)
                          if narrations.get(c.identifiant)), hook_text)
        derniere = re.split(r"(?<=[.!?…])\s+", precedent.strip())[-1] if precedent else hook_text
        valeurs = {**commun, "hook_text": hook_text, "plan_resume": plan_resume,
                   "deja_dit": deja_dit, "phrase_precedente": derniere,
                   "segments_a_ecrire": "\n".join(lignes)}
        donnees, _ = llm.generate_json(
            remplir(gabarit, valeurs), system=systeme, json_schema=SCHEMA_NARRATION,
            # Large volontairement : une réponse coupée fait échouer l'appel, un excès de mots
            # est retaillé par `_retailler`. Plafonné pour rester dans les 8 k de contexte.
            max_tokens=min(4200, int(sum(budgets[c.identifiant] for c in lot) * 4.5) + 400),
            temperature=0.7, seed=spec.seed % 100000 + debut,
            etiquette=f"{etiquette}:{lot[0].identifiant}", trace=trace, racine=racine,
        )
        attendus = {c.identifiant for c in lot}
        for entree in donnees["segments"]:
            identifiant = str(entree.get("id", "")).strip()
            if identifiant not in attendus:
                chiffres = re.findall(r"\d+", identifiant)
                identifiant = f"seg_{int(chiffres[-1]):02d}" if chiffres else ""
            if identifiant in attendus:
                narrations[identifiant] = _normaliser_capitales(
                    re.sub(r"\s+", " ", str(entree.get("narration", ""))).strip())
