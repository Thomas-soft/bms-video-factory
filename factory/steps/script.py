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
    ErreurRun,
    Hook,
    Interrupt,
    LignesDivulgation,
    Research,
    Script,
    ScriptSegment,
    SignatureEditoriale,
)
from factory.core.paths import RunPaths, racine_projet
from factory.retention import density as density_module
from factory.retention import hooks as hooks_module
from factory.retention import interrupts as interrupts_module
from factory.retention import loops as loops_module
from factory.retention import patterns as patterns_module
from factory.retention import verify as verify_module
# Import tardif volontaire dans les fonctions ? Non : `review` ne tire que le noyau et
# l'orchestrateur ne tire pas `steps`, il n'y a donc pas de cycle.
from factory.orchestrator import review as review_module

#: Multiplicateur du rythme de coupe qui donne la cadence des ruptures (prompt étape 10).
#: Conservé ici pour le **nombre de segments** ; la cadence des ruptures elle-même est calculée
#: par `factory/retention/interrupts.py`, qui la borne à [20, 45] s (étape 16).
FACTEUR_RUPTURE = 4
#: Essais de régénération ciblée après une vérification de rétention en échec (étape 16).
ESSAIS_RETENTION = 3
#: Multiplie le plafond de jetons des passes de réparation (voir `_ecrire_lots`). 2,2 place
#: un segment de 212 mots à ~2 500 jetons, loin du plafond dur de 4 200 et de la fenêtre de 8 k.
MARGE_JETONS_REPARATION = 2.2
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
    # Étape 16 : ce que la vérification de rétention a trouvé, et ce qu'il a fallu de reprises.
    rapport: Any | None = None
    regenerations: int = 0
    echec: str | None = None


# --------------------------------------------------------------------------------------
# Gabarits de prompt
# --------------------------------------------------------------------------------------

def _sections(chemin: Path) -> dict[str, str]:
    """Sections `##` d'un fichier de gabarits."""
    sections: dict[str, str] = {}
    courante: str | None = None
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.startswith("## "):
            courante = ligne[3:].strip()
            sections[courante] = ""
        elif courante:
            sections[courante] += ligne + "\n"
    return {cle: valeur.strip() for cle, valeur in sections.items()}


def charger_gabarits(lang: str, racine: Path | None = None) -> dict[str, str]:
    """Sections `##` de `factory/prompts/script_<lang>.md`, **repli section par section**.

    Le repli était jusqu'ici sur le fichier entier : une langue dont le fichier existait mais à
    qui manquait une section levait un `KeyError` au milieu d'un run. Les sections ajoutées à
    l'étape 16 (`hooks`, `regeneration`, `enrichissement`) n'existent qu'en anglais — la
    production est en anglais (décision d'Alek du 15/09/2026) et l'étape 24 est différée.
    """
    dossier = (racine or racine_projet()) / "factory" / "prompts"
    anglais = _sections(dossier / "script_en.md")
    chemin = dossier / f"script_{lang}.md"
    if not chemin.exists():
        return anglais
    return {**anglais, **_sections(chemin)}


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
    duree_cible_s: float, intervalle_rupture_s: float, boucles_minimum: int = 2,
    position: str = "apres_premier_point",
) -> list[Case]:
    """Rôles, boucles ouvertes, ruptures et budget de mots — avant le premier appel au LLM.

    Boucles (`factory/retention/loops.py`) : l'accroche plante la première, le segment suivant
    plante la seconde, et les deux sont payées avant la conclusion. Ruptures
    (`factory/retention/interrupts.py`) : une par tranche de `intervalle_rupture_s`.
    """
    roles: list[str] = ["hook", "contexte"]
    # `apres_conclusion` / `fin` (étape 27) : le segment sponsor est l'appel à l'action
    # produit, posé après la conclusion ; le reste du squelette est celui d'un run sans produit.
    en_fin = avec_sponsor and position in ("apres_conclusion", "fin")
    total = n_segments - 1 if en_fin else n_segments
    dernier = total - 1
    position_sponsor = 3 if avec_sponsor and not en_fin else None
    for i in range(2, total):
        if i == position_sponsor:
            roles.append("sponsor")
        elif i == dernier:
            roles.append("conclusion")
        elif i == dernier - 1:
            roles.append("cta")
        else:
            roles.append("point")
    if en_fin:
        roles.append("sponsor")

    boucles = loops_module.planifier(roles, minimum=boucles_minimum)

    cases: list[Case] = []
    mots_hook = min(mots_hook_max, max(20, mots_cibles // n_segments))
    reste = max(1, mots_cibles - mots_hook)
    autres = n_segments - 1
    for i, role in enumerate(roles):
        mots = mots_hook if i == 0 else round(reste / autres)
        cases.append(Case(index=i, role=role, open_loop=boucles[i], mots=mots))

    # Ruptures : une par tranche de `intervalle_rupture_s`, posée sur le segment qui contient
    # l'instant visé (étape 16). L'ancienne règle posait une rupture sur *chaque* segment assez
    # long, ce qui donnait 27 ruptures sur un run de 12 min — c'est-à-dire aucune.
    durees = [duree_cible_s * c.mots / max(1, mots_cibles) for c in cases]
    plan_ruptures = interrupts_module.planifier(durees, roles, intervalle_rupture_s, seed)
    for case, rupture in zip(cases, plan_ruptures.par_segment):
        case.interrupt = rupture
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

SCHEMA_CANDIDATS = {
    "type": "object",
    "properties": {"hooks": {"type": "array", "minItems": 1, "items": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "on_screen_text": {"type": "string"},
                       "visual_intent": {"type": "string"}},
        "required": ["text", "on_screen_text", "visual_intent"]}}},
    "required": ["hooks"],
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

def _accroche(
    gabarits: dict[str, str], commun: dict[str, Any], systeme: str, hook_type: str,
    taxonomie: dict[str, Any], patterns: patterns_module.Patterns, spec: Any,
    mots_hook_max: int, mots_hook_min: int, trace: llm.TraceLLM, racine: Path | None,
    alertes: list[str], decalage: int = 0,
) -> hooks_module.Choix:
    """Génère `N_CANDIDATS` accroches du type tiré, les note, et fait départager les deux
    meilleures par le modèle.

    `decalage` décale la graine : c'est ce qui rend une **seconde** tentative différente de la
    première quand la vérification a rejeté toutes les accroches du premier tirage.
    """
    exemples = taxonomie.get("exemples") or []
    exemple = next((e["verbatim"] for e in exemples if e.get("langue") == spec.lang),
                   exemples[0]["verbatim"] if exemples else "—")
    patron = patterns.patron(hook_type)
    valeurs = {
        **commun,
        "hook_type": hook_type,
        "hook_definition": taxonomie.get("definition", ""),
        "hook_regles": "\n".join(f"- {r}" for r in taxonomie.get("regles", [])),
        "hook_exemple": exemple[:300],
        # Le plancher était **noté mais jamais dit** : le barème retirait des points sous le
        # p25 de la niche (22 mots sur `science_pop`) alors que le prompt n'annonçait qu'un
        # plafond. Les trois tirages rendaient 18 mots, et le hook passait « malgré »
        # l'infraction (mesuré sur `avwf`, 18/09/2026).
        "hook_mots_max": mots_hook_max,
        "hook_mots_min": mots_hook_min,
        "hook_patron": patron.texte if patron else "(no pattern measured for this type)",
        "n_candidats": hooks_module.N_CANDIDATS,
        "formulations_proscrites": ", ".join(
            f'"{f}"' for f in patterns.formulations_proscrites[:12]),
    }
    graine = (spec.seed % 100000) + decalage * 977
    donnees, _ = llm.generate_json(
        remplir(gabarits["hooks"], valeurs), system=systeme, json_schema=SCHEMA_CANDIDATS,
        max_tokens=900, temperature=0.9, seed=graine,
        etiquette=f"script:hooks#{decalage}", trace=trace, racine=racine,
    )
    candidats: list[hooks_module.Candidat] = []
    for entree in (donnees.get("hooks") or [])[: hooks_module.N_CANDIDATS]:
        texte = _normaliser_capitales(re.sub(r"\s+", " ", str(entree.get("text", ""))).strip())
        if not texte:
            continue
        candidat = hooks_module.noter(texte, hook_type, mots_hook_max, patterns,
                                      plancher_mots=mots_hook_min)
        candidat.on_screen_text = _texte_ecran(entree.get("on_screen_text"))
        candidat.visual_intent = str(entree.get("visual_intent") or "").strip()[:500]
        candidats.append(candidat)
    if not candidats:
        raise RuntimeError("accroche : le modèle n'a rendu aucun candidat exploitable")
    if len(candidats) < hooks_module.N_CANDIDATS:
        alertes.append(f"hook : {len(candidats)} candidat(s) rendus pour "
                       f"{hooks_module.N_CANDIDATS} demandés")

    gagnant, motif = hooks_module.choisir(
        candidats, hook_type, str(commun.get("sujet", "")),
        str(taxonomie.get("definition", "")), seed=graine, racine=racine, trace=trace)
    if gagnant.infractions:
        alertes.append("hook retenu malgré : " + " ; ".join(gagnant.infractions))
    return hooks_module.Choix(type=hook_type, part=0.0, candidats=candidats, choisi=gagnant,
                              motif=motif)


def _verifier_et_regenerer(
    script: Script, assembler: Any, narrations: dict[str, str], cases: list[Case],
    plan: dict[str, dict[str, Any]], gabarits: dict[str, str], commun: dict[str, Any],
    systeme: str, plan_resume: str, hook_text: str, produit: Any, cfg: Any, channel: Any,
    spec: Any, trace: llm.TraceLLM, racine: Path | None, faits_par_id: dict[str, str],
    recherche: Research, *, patterns: patterns_module.Patterns, niche: str, mpm: float,
    mots_hook_max: int, mots_hook_min: int, boucles_minimum: int, tolerance: float,
    densite_cible: float | None, densite_plancher: float | None, alertes: list[str],
) -> tuple[verify_module.Rapport, int, list[str]]:
    """Vérifie, régénère les segments fautifs, recommence — trois essais au maximum.

    Chaque essai fait au plus deux passes d'écriture : **l'enrichissement** (quand la densité
    est sous la cible, avec les faits de `research.json` et l'interdiction d'en inventer) puis
    **la régénération** (les autres infractions, listées mot pour mot dans le prompt). Le hook,
    lui, ne se réécrit pas segment par segment : il est re-tiré en entier, avec une graine
    décalée, pour ne pas reproposer les mêmes trois candidats.

    Rend `(dernier rapport, nombre d'essais, historique des infractions)`. La décision d'échouer
    le run appartient à l'appelant : ce module constate.
    """
    par_id = {c.identifiant: c for c in cases}
    historique: list[str] = []
    rapport = _verifier(script, patterns=patterns, niche=niche, spec=spec, mpm=mpm,
                        mots_hook_max=mots_hook_max, mots_hook_min=mots_hook_min,
                        boucles_minimum=boucles_minimum, tolerance=tolerance,
                        densite_cible=densite_cible, recherche=recherche, racine=racine,
                        trace=trace)
    essais = 0
    while not rapport.conforme and essais < ESSAIS_RETENTION:
        essais += 1
        historique.append(f"essai {essais} : "
                          + " | ".join(str(i) for i in rapport.bloquantes))
        codes = {i.code for i in rapport.bloquantes}
        # Une passe de réparation qui épuise ses trois essais LLM lève `ErreurLLM`. Sans ce
        # garde, elle remontait en traceback et le run n'avait **ni statut `failed` ni motif**
        # — ce que le « Terminé quand » de l'étape 16 exige explicitement (mesuré le
        # 18/09/2026 sur `script:densite3:seg_18`). L'échec est ici une infraction de plus,
        # portée par le rapport, et le run se termine proprement en `failed`.
        try:

            # Le hook n'est pas réécrit ici : il a déjà été re-tiré jusqu'à trois fois par
            # `executer` avant l'écriture de la narration (une accroche se rejoue, elle ne se
            # rapièce pas). S'il reste en infraction, c'est un motif d'échec du run.

            infraction_densite = next(
                (i for i in rapport.bloquantes if i.code == "densite_sous_cible"), None)
            if infraction_densite is not None and infraction_densite.segments:
                lot = [par_id[i] for i in infraction_densite.segments if i in par_id]
                if lot:
                    gabarit = remplir(gabarits["enrichissement"], {
                        **commun,
                        "densite_mesuree": (f"{rapport.densite.faits_par_minute:.2f}"
                                            if rapport.densite else "—"),
                        "densite_cible": f"{densite_cible:.2f}" if densite_cible else "—",
                    }, strict=False)
                    _ecrire_lots(lot, {c.identifiant: c.mots for c in lot}, narrations, plan, cases,
                                 gabarits, commun, systeme, plan_resume, hook_text, produit, cfg,
                                 channel, spec, trace, racine,
                                 f"script:densite{essais}", faits_par_id, gabarit_force=gabarit,
                                 facteur_jetons=MARGE_JETONS_REPARATION)

            autres = [i for i in rapport.bloquantes
                      if i.code not in {"densite_sous_cible", "hook"}]
            cibles = []
            for infraction in autres:
                for identifiant in infraction.segments:
                    case = par_id.get(identifiant)
                    if case is not None and case.role != "hook" and case not in cibles:
                        cibles.append(case)
            if cibles:
                gabarit = remplir(gabarits["regeneration"], {
                    **commun, "infractions": rapport.consignes(), "hook_text": hook_text,
                }, strict=False)
                _ecrire_lots(cibles, {c.identifiant: c.mots for c in cibles}, narrations, plan,
                             cases, gabarits, commun, systeme, plan_resume, hook_text, produit,
                             cfg, channel, spec, trace, racine,
                             f"script:regeneration{essais}", faits_par_id, gabarit_force=gabarit,
                             facteur_jetons=MARGE_JETONS_REPARATION)
            elif infraction_densite is None and "hook" not in codes:
                # Aucune infraction ne nomme de segment réécrivable : insister ne changerait rien.
                alertes.append("vérification : infraction non corrigible par réécriture de segment "
                               f"— {', '.join(sorted(codes))}")
                break

        except llm.ErreurLLM as erreur:
            # Le message exact de l'outil, jamais reformulé : c'est lui qui dira à Thomas
            # si le modèle a saturé le plafond ou si le sous-processus est tombé.
            historique.append(f"essai {essais} : réparation abandonnée — {erreur}")
            alertes.append(f"réparation LLM abandonnée à l'essai {essais} : {erreur}")
            break
        # Les passes de réparation réécrivent sans retailler : sans ce rappel, l'enrichissement
        # rallongeait le script de 55,7 % au-dessus de la cible et `duree_hors_tolerance`
        # remplaçait simplement l'infraction qu'on venait de corriger (mesuré sur `avwf`,
        # 18/09/2026). La boucle de durée, elle, retaille après chaque correction : même règle
        # ici, et toujours sans appeler le modèle.
        for case in _retaillables(cases):
            narrations[case.identifiant] = _retailler(
                narrations.get(case.identifiant, ""), case.mots)
        script = assembler()
        rapport = _verifier(script, patterns=patterns, niche=niche, spec=spec, mpm=mpm,
                            mots_hook_max=mots_hook_max, mots_hook_min=mots_hook_min,
                            boucles_minimum=boucles_minimum, tolerance=tolerance,
                            densite_cible=densite_cible, recherche=recherche, racine=racine,
                            trace=trace)
    return rapport, essais, historique


def _verifier(
    script: Script, *, patterns: patterns_module.Patterns, niche: str, spec: Any, mpm: float,
    mots_hook_max: int, mots_hook_min: int, boucles_minimum: int, tolerance: float,
    densite_cible: float | None, recherche: Research, racine: Path | None,
    trace: llm.TraceLLM,
) -> verify_module.Rapport:
    """Appel de `verify.verifier` avec les seuils du run — un seul endroit où ils sont lus."""
    return verify_module.verifier(
        script, niche=niche, lang=spec.lang, mots_par_minute=mpm,
        plafond_hook_mots=mots_hook_max, plancher_hook_mots=mots_hook_min,
        boucles_minimum=boucles_minimum, cut_rhythm_target_s=spec.cut_rhythm_target_s,
        duree_cible_s=float(spec.target_duration_s), tolerance_duree=tolerance,
        patterns=patterns, densite_cible=densite_cible, recherche=recherche,
        seed=spec.seed % 100000, racine=racine, trace=trace,
    )


def verifier_run(video_id: str, racine: Path | None = None,
                 juge_boucles: bool = False) -> verify_module.Rapport:
    """Re-vérifie le `script.json` **déjà écrit** d'un run, avec les seuils de sa niche.

    Point d'entrée de la relecture éditée à la main (`factory review`, touche `e`) : un
    script retouché dans `$EDITOR` doit repasser exactement le contrôle que la machine
    applique au sien, sinon l'édition humaine devient une porte dérobée autour du seul
    contrôle automatique du texte.

    `juge_boucles` est **faux** par défaut, et c'est la seule différence avec la vérification
    de production : le juge de boucles appelle le LLM, donc charge un modèle de 6,6 Go. La
    règle « un seul modèle résident » (`CLAUDE.md` § 4) interdit de le faire pendant qu'un
    relecteur tient son terminal, et les règles de boucle sont déjà vérifiées par le modèle
    pydantic (`Script._regles_de_script`).
    """
    racine = racine or racine_projet()
    spec = runs.charger_spec(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    chemins = RunPaths.depuis_video_id(video_id, racine)
    script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))
    recherche = (Research.model_validate_json(chemins.research.read_text(encoding="utf-8"))
                 if chemins.research.exists() else None)
    mpm = referentiel.mots_par_minute(spec.niche, racine)
    bloc_hook = referentiel.niche(spec.niche, racine)["hooks"]["longueur_mots"]
    mots_hook_max = referentiel.longueur_hook_max(spec.niche, racine)
    return verify_module.verifier(
        script, niche=spec.niche, lang=spec.lang, mots_par_minute=mpm,
        plafond_hook_mots=mots_hook_max,
        plancher_hook_mots=int(round(float(bloc_hook.get("p25") or mots_hook_max * 0.6))),
        boucles_minimum=referentiel.boucles_minimum(spec.niche, racine),
        cut_rhythm_target_s=spec.cut_rhythm_target_s,
        duree_cible_s=float(spec.target_duration_s),
        tolerance_duree=float(cfg.niches[spec.niche].duree_s.tolerance),
        patterns=patterns_module.charger(spec.lang, racine),
        densite_cible=density_module.cible(spec.niche, racine), recherche=recherche,
        juge_boucles=juge_boucles, seed=spec.seed % 100000, racine=racine,
    )


def executer(video_id: str, racine: Path | None = None) -> ResultatScript:
    """Tire le hook, écrit le plan, l'accroche puis la narration, et cale la durée."""
    t0 = time.perf_counter()
    alertes: list[str] = []
    spec = runs.charger_spec(video_id, racine)
    if spec.parent_id:
        # Déclinaison (étape 24) : le script s'adapte depuis le parent, il ne s'écrit pas.
        from factory.steps import localize as localize_module
        return localize_module.adapter_script(video_id, racine)
    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.research.exists():
        raise FileNotFoundError(f"research.json absent : lance `factory research --run {video_id}`")
    recherche = Research.model_validate_json(chemins.research.read_text(encoding="utf-8"))

    mpm = referentiel.mots_par_minute(spec.niche, racine)
    mots_cibles = int(round(spec.target_duration_s * mpm / 60))
    tolerance = float(cfg.niches[spec.niche].duree_s.tolerance)
    # Le nombre de segments suit toujours 4 × le rythme de coupe (étape 10) ; la cadence des
    # ruptures, elle, est bornée à [20, 45] s par l'étape 16. Les deux peuvent diverger sur une
    # niche à plans très longs, et c'est voulu : un segment n'est pas une rupture.
    intervalle_segments = FACTEUR_RUPTURE * spec.cut_rhythm_target_s
    cadence_ruptures = interrupts_module.intervalle_s(spec.cut_rhythm_target_s)
    n_segments = max(SEGMENTS_MIN,
                     min(SEGMENTS_MAX, round(spec.target_duration_s / intervalle_segments)))
    mots_hook_max = referentiel.longueur_hook_max(spec.niche, racine)
    bloc_hook = referentiel.niche(spec.niche, racine)["hooks"]["longueur_mots"]
    mots_hook_min = int(round(float(bloc_hook.get("p25") or mots_hook_max * 0.6)))
    boucles_minimum = referentiel.boucles_minimum(spec.niche, racine)
    patterns = patterns_module.charger(spec.lang, racine)
    densite_cible = density_module.cible(spec.niche, racine)
    densite_plancher = density_module.plancher(spec.niche, racine)

    hook_type, hook_part = hooks_module.tirer_type(spec.niche, spec.seed, racine)
    taxonomie = referentiel.taxonomie_hooks(racine)[hook_type]

    produit = cfg.products.get(spec.product_id) if spec.product_id else None
    cases = construire_squelette(
        n_segments, mots_cibles, mots_hook_max, produit is not None, spec.seed,
        float(spec.target_duration_s), cadence_ruptures, boucles_minimum,
        position=produit.cta_segment.position if produit is not None else "apres_premier_point",
    )
    gabarits = charger_gabarits(spec.lang, racine)
    systeme = gabarits["systeme"]
    # Motifs de rejet du relecteur et consignes des remèdes du banc (étape 22.2). Versés
    # dans l'invite **système**, donc présents à chaque appel de l'étape — plan, accroche,
    # narration, réparations. Un motif qui n'atteindrait que le plan laisserait le modèle
    # réécrire la même narration, et le rejet n'aurait servi à rien.
    consignes = review_module.bloc_consignes(chemins)
    if consignes:
        systeme += consignes
        alertes.append(f"{len(review_module.lire_consignes(chemins))} consigne(s) de "
                       "relecture ou de régénération versées au prompt")
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
        # Les marqueurs de boucle servaient **uniquement à vérifier** : le modèle était jugé
        # sur un vocabulaire qu'on ne lui avait jamais montré, d'où 0 boucle payée sur 2
        # exigées au run `avwf` du 18/09/2026. `patterns_en.yaml` annonce d'ailleurs
        # `phrases_paiement` comme « à donner au modèle ». Ce sont des connecteurs de
        # rétention, pas du contenu : les citer n'est pas recopier le corpus.
        "marqueurs_plantation": ", ".join(
            f'"{m}"' for m in patterns.marqueurs_plantation[:8]),
        "marqueurs_paiement": ", ".join(
            f'"{m}"' for m in patterns.marqueurs_paiement[:8]),
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

    # 2 — accroche : trois candidats du type tiré, notés par règles, les deux meilleurs en duel.
    # Re-tirée tant qu'aucun des trois candidats n'est acceptable, trois tirages au plus : une
    # accroche refusée ne se réécrit pas phrase à phrase, elle se rejoue.
    choix = _accroche(gabarits, commun, systeme, hook_type, taxonomie, patterns, spec,
                      mots_hook_max, mots_hook_min, trace, racine, alertes, decalage=0)
    tirages_hook = 1
    while not choix.choisi.acceptable and tirages_hook < ESSAIS_RETENTION:
        alertes.append(
            f"hook : tirage {tirages_hook} refusé ({choix.choisi.score:.0f}/100 — "
            + " ; ".join(choix.choisi.infractions) + "), re-tirage")
        tirages_hook += 1
        choix = _accroche(gabarits, commun, systeme, hook_type, taxonomie, patterns, spec,
                          mots_hook_max, mots_hook_min, trace, racine, alertes,
                          decalage=tirages_hook - 1)
    hook_text = choix.choisi.texte
    hook_donnees = {"on_screen_text": choix.choisi.on_screen_text,
                    "visual_intent": choix.choisi.visual_intent}

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

    # 5 — assemblage.
    lignes = _lignes_divulgation(produit, cfg, spec.lang) if produit is not None else None

    def _assembler() -> Script:
        """Reconstruit l'objet `Script` à partir de l'état courant des narrations."""
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
                          if spec.lang == "fr"
                          else "Close shot on an object of the topic, no person.")
            sources = [s for s in (entree.get("sources") or [])
                       if isinstance(s, str) and s in {f.id for f in recherche.facts}]
            segments.append(ScriptSegment(
                id=case.identifiant, role=case.role, narration=narration, on_screen_text=ecran,
                visual_intent=visuel[:500], open_loop=case.open_loop, interrupt=case.interrupt,
                sources=sources,
                disclosure_spoken=(case.role == "sponsor"),
            ))
        mots = sum(s.word_count for s in segments)
        return Script(
            lang=spec.lang,
            hook=Hook(type=hook_type, text=hook_text),
            segments=segments,
            editorial_signature=SignatureEditoriale(
                angle=recherche.angle_signature,
                elements_proprietaires=recherche.elements_proprietaires or [recherche.angle],
            ),
            word_count=mots, estimated_duration_s=round(mots / (mpm / 60), 1),
            disclosure_lines=lignes,
        )

    manquant_visuel = [c.identifiant for c in cases
                       if c.role != "hook" and not str(
                           plan.get(c.identifiant, {}).get("visual_intent") or "").strip()]
    if manquant_visuel:
        alertes.append(f"{len(manquant_visuel)} intention(s) visuelle(s) absente(s), repli "
                       f"générique : {', '.join(manquant_visuel[:5])}")

    script = _assembler()

    # 6 — vérification de rétention, et régénération ciblée (étape 16).
    t_verif = time.perf_counter()
    rapport, essais, historique = _verifier_et_regenerer(
        script, _assembler, narrations, cases, plan, gabarits, commun, systeme, plan_resume,
        hook_text, produit, cfg, channel, spec, trace, racine, faits_par_id, recherche,
        patterns=patterns, niche=spec.niche, mpm=mpm, mots_hook_max=mots_hook_max,
        mots_hook_min=mots_hook_min, boucles_minimum=boucles_minimum,
        tolerance=tolerance, densite_cible=densite_cible, densite_plancher=densite_plancher,
        alertes=alertes,
    )
    script = _assembler()
    duree = script.estimated_duration_s
    secondes_verif = time.perf_counter() - t_verif
    runs.ecrire_json(chemins.script, script)

    segments = script.segments
    mots_total = script.word_count
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
                       " — signalés, non bloquants ; seules les sources inventées sont filtrées")

    secondes = time.perf_counter() - t0
    manifest = runs.charger_manifest(video_id, racine)
    manifest.decisions.hook_type = hook_type
    from factory.analytics import weights as wmod
    wmod.noter(manifest, wmod.charger(racine), "hook_parts",
               "appris" if hooks_module.parts_apprises(spec.niche, racine) else "référentiel")
    manifest.decisions.duration_s = round(duree, 1)
    # Étape 16 : les trois candidats notés, le choisi, et pourquoi.
    from factory.core.models import CandidatHook, DensiteMesuree, VerificationRetention
    manifest.decisions.hook_candidates = [
        CandidatHook(text=c.texte, words=c.mots, score=round(min(100.0, c.score), 1),
                     violations=list(c.infractions)) for c in choix.candidats]
    manifest.decisions.hook_chosen = choix.choisi.texte
    manifest.decisions.hook_choice_reason = choix.motif
    # `density_facts_per_min` mesurait jusqu'ici les **faits cités** de `research.json` par
    # minute, ce qui compte les sources et non l'information reçue par le spectateur. Il porte
    # désormais la mesure de `factory/retention/density.py`, faite sur le texte parlé ; le
    # comptage par sources reste lisible dans `density.by_category` du bloc ci-dessous.
    comptage = rapport.densite or density_module.mesurer_script(script, mpm)
    juge = density_module.juger(script, mpm, seed=spec.seed % 100000, racine=racine, trace=trace)
    manifest.decisions.density_facts_per_min = comptage.faits_par_minute
    manifest.decisions.density = DensiteMesuree(
        facts_per_min=comptage.faits_par_minute,
        facts_per_min_weighted=comptage.faits_pondere_par_minute,
        target=densite_cible, floor=densite_plancher, count=comptage.total,
        entity_share=comptage.part_entites, by_category=comptage.par_categorie,
        judge_facts_per_min=None if juge is None else juge.faits_par_minute,
        judge_specificity=None if juge is None else juge.specificite,
        judge_vagueness=None if juge is None else juge.vague,
    )
    plantees_marquees, payees_verifiees = loops_module.resume(rapport.boucles)
    manifest.decisions.retention = VerificationRetention(
        regenerations=essais,
        violations=[str(i) for i in rapport.infractions],
        historique=historique,
        interrupts_planned=rapport.ruptures_posees,
        interrupt_cadence_s=rapport.cadence_s,
        interrupt_max_gap_s=rapport.ecart_rupture_max_s,
        loops_planted_marked=plantees_marquees,
        loops_paid_verified=payees_verifiees,
        loops_unjudged=sum(1 for b in rapport.boucles if b.coherente is None),
        seconds=round(secondes_verif, 2),
    )
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
    # `trace.secondes` compte les relectures de cache à leur durée d'origine : il dépasse donc
    # le temps réel de l'étape et ne répond pas à « combien coûte un run ». Les deux sont
    # enregistrés, et c'est `script_llm_calcule` qui chiffre le temps réellement passé à générer.
    manifest.execution.timings["script_llm"] = round(trace.secondes, 2)
    manifest.execution.timings["script_llm_calcule"] = round(trace.secondes_calculees, 2)
    manifest.execution.timings["script_appels"] = len(trace.appels)
    manifest.execution.timings["script_appels_caches"] = trace.appels_caches
    # Échec explicite du run (prompt de l'étape 16). Deux seuils, deux conséquences : une
    # infraction de rétention non corrigée en trois essais fait échouer ; la densité, elle, ne
    # fait échouer que sous le **plancher** de la niche — motif dans `density.plancher`.
    motifs_echec = [str(i) for i in rapport.bloquantes if i.code != "densite_sous_cible"]
    if (densite_plancher is not None
            and comptage.faits_par_minute < densite_plancher):
        motifs_echec.append(
            f"densite_sous_plancher : {comptage.faits_par_minute:.2f} fait(s)/min sous le "
            f"plancher de {densite_plancher:.2f} de la niche {spec.niche}")
    if motifs_echec:
        manifest.execution.run_state = "failed"
        manifest.execution.blocked_reason = (
            f"script refusé par la vérification de rétention après {essais} régénération(s) : "
            + " ; ".join(motifs_echec)
        )
        manifest.execution.errors.append(ErreurRun(
            step="script", ts=runs.maintenant(), code=4,
            message=" ; ".join(motifs_echec), retry=essais,
        ))
    else:
        manifest.execution.run_state = "awaiting_review"
        # Une étape rejouée qui réussit doit effacer le motif du refus précédent : sans cela
        # le manifeste du run 6 d'`avwf` affichait `awaiting_review` **et** le motif d'échec
        # du run 5 (18/09/2026), ce qui se lit comme un run en échec.
        manifest.execution.blocked_reason = None
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
                          alertes, trace, rapport=rapport, regenerations=essais,
                          echec=manifest.execution.blocked_reason if motifs_echec else None)


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
    facteur_jetons: float = 1.0,
) -> None:
    """Écrit la narration par lots de `LOT` segments ; chaque lot est un appel qui se termine.

    `facteur_jetons` élargit le **plafond de jetons** sans toucher à la consigne de longueur
    donnée au modèle. Les passes de réparation en ont besoin : mesuré le 18/09/2026, la passe
    d'enrichissement de densité fait saturer le plafond au 9B quantifié — il empile des phrases
    courtes au lieu d'ajouter un fait — et une réponse coupée est un JSON déséquilibré, donc
    trois essais perdus à 240 s pièce. Le plafond n'autorise pas ces mots, il permet à l'objet
    de se refermer : `_retailler` ramène ensuite la narration à son budget.
    """
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
                # Après la conclusion (étape 27) : gabarit d'appel à l'action, même mention.
                en_fin = produit.cta_segment.position in ("apres_conclusion", "fin")
                gabarit = gabarits["sponsor_cta"] if en_fin and "sponsor_cta" in gabarits \
                    else gabarits["sponsor"]
                consigne += "\n" + remplir(gabarit, {
                    "produit": produit.name,
                    "phrase_divulgation": _lignes_divulgation(produit, cfg, spec.lang).spoken_line,
                    "cta_text": produit.cta_text.get(spec.lang, ""),
                    "duree_s_max": f"{produit.cta_segment.duree_s_max:.0f}",
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
            max_tokens=min(4200, int(sum(budgets[c.identifiant] for c in lot)
                                     * 4.5 * facteur_jetons) + 400),
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
