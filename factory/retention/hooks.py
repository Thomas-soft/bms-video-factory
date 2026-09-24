"""Accroche : tirage du type, trois candidats, note par règles, duel LLM, choix tracé.

**Ce qui change par rapport à l'étape 10.** Le hook était généré **une fois**, tronqué s'il
dépassait, et posé au script sans qu'aucune règle ne le refuse. Ici il est généré trois fois,
noté par des règles mécaniques (longueur mesurée de la niche, aucune formulation proscrite,
élément clé du type présent), et les deux meilleurs sont départagés par le modèle. Les trois
candidats et leur note entrent au manifeste : c'est ce que l'étape 26 corrélera aux vues.

**Pourquoi un duel plutôt qu'une note LLM absolue.** Un 9B quantifié note tout entre 7 et 9 ;
il compare en revanche correctement deux textes courts. La comparaison est aussi moins chère
qu'une grille : un appel de 120 jetons contre trois.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from factory import llm
from factory.core import referentiel as ref_module
from factory.retention.patterns import Patterns, normaliser

#: Nombre de candidats générés par run (prompt de l'étape 16).
N_CANDIDATS = 3

#: Pénalités de la note par règles, sur 100. Un hook qui viole une règle dure tombe sous la
#: barre des candidats acceptables ; les règles molles ne font que départager.
# Les deux règles dures — formulation proscrite, élément clé absent — doivent à elles seules
# faire tomber sous `SCORE_ACCEPTABLE`. Les règles molles (longueur) ne font que départager :
# dix mots de trop coûtent trente points et laissent le candidat utilisable.
PENALITE_PROSCRITE = 45.0
PENALITE_ELEMENT_ABSENT = 55.0
PENALITE_MOT_EN_TROP = 3.0
PENALITE_MOT_MANQUANT = 1.5
#: En deçà, un candidat est jugé inutilisable et n'entre pas au duel.
SCORE_ACCEPTABLE = 60.0


# --------------------------------------------------------------------------------------
# Éléments clés : la part mécaniquement vérifiable de chaque type
# --------------------------------------------------------------------------------------

def _a_question(texte: str, lexique: list[str]) -> bool:
    """Une question, à l'interrogation ou au mot interrogatif.

    Le « ? » ne suffit pas : le modèle l'oublie une fois sur trois et les transcriptions
    auto-générées du corpus n'en portent aucun. Le lexique porte les amorces mesurées.
    """
    return "?" in texte or _contient(texte, lexique)


def _a_chiffre(texte: str, lexique: list[str]) -> bool:
    """Un nombre en chiffres, ou un nombre écrit en toutes lettres (le TTS veut des lettres)."""
    return bool(re.search(r"\d", texte)) or _contient(texte, lexique)


def _a_contradiction(texte: str, lexique: list[str]) -> bool:
    return _contient(texte, lexique)


def _a_enjeu(texte: str, lexique: list[str]) -> bool:
    """Première personne : c'est ce qui distingue l'enjeu personnel de l'adresse directe."""
    return bool(re.search(r"\b(i|i'm|i've|my|me|mine)\b", texte.lower())) or _contient(
        texte, lexique)


def _a_adresse(texte: str, lexique: list[str]) -> bool:
    return bool(re.search(r"\b(you|your|yours|you're|you've)\b", texte.lower())) or _contient(
        texte, lexique)


def _a_enumeration(texte: str, lexique: list[str]) -> bool:
    return bool(re.search(r"\d", texte)) and _contient(texte, lexique)


def _a_action(texte: str, _lexique: list[str]) -> bool:
    """`in_medias_res` : ni deuxième personne ni question dans les 15 premiers mots.

    La règle de sens du référentiel (« verbe d'action conjugué décrivant un événement en
    cours ») n'est pas vérifiable sans modèle ; sa part mécanique l'est, et c'est elle seule
    que la note applique — comme au banc (`hook_type_rules`).
    """
    debut = " ".join(texte.split()[:15]).lower()
    return not re.search(r"\b(you|your|yours)\b", debut) and "?" not in debut


def _generique(texte: str, lexique: list[str]) -> bool:
    """Élément attesté par son seul lexique (mystère, autorité, mise en scène)."""
    return _contient(texte, lexique)


def _contient(texte: str, lexique: list[str]) -> bool:
    cible = normaliser(texte)
    return any(normaliser(mot) in cible for mot in lexique)


VERIFICATEURS = {
    "question": _a_question,
    "chiffre": _a_chiffre,
    "contradiction": _a_contradiction,
    "enjeu": _a_enjeu,
    "adresse": _a_adresse,
    "enumeration": _a_enumeration,
    "action": _a_action,
    "mystere": _generique,
    "autorite": _generique,
    "scene": _generique,
}


# --------------------------------------------------------------------------------------
# Note par règles
# --------------------------------------------------------------------------------------

@dataclass
class Candidat:
    """Un hook proposé, sa note et ce qu'on lui reproche."""

    texte: str
    on_screen_text: str | None = None
    visual_intent: str = ""
    score: float = 0.0
    infractions: list[str] = field(default_factory=list)

    @property
    def mots(self) -> int:
        return len(self.texte.split())

    @property
    def acceptable(self) -> bool:
        return self.score >= SCORE_ACCEPTABLE

    def json(self) -> dict[str, Any]:
        """Entrée `hook_candidates[]` du manifeste."""
        return {"text": self.texte, "words": self.mots, "score": round(self.score, 1),
                "violations": list(self.infractions)}


def noter(
    texte: str, type_hook: str, plafond_mots: int, patterns: Patterns,
    plancher_mots: int | None = None,
) -> Candidat:
    """Note un hook sur 100 par les seules règles, et nomme chaque infraction en clair."""
    candidat = Candidat(texte=texte.strip())
    score = 100.0

    mots = candidat.mots
    if mots > plafond_mots:
        trop = mots - plafond_mots
        score -= trop * PENALITE_MOT_EN_TROP
        candidat.infractions.append(
            f"longueur : {mots} mots pour un plafond de {plafond_mots} (médiane de la niche)")
    elif plancher_mots is not None and mots < plancher_mots:
        # Objection déjà tranchée au banc (B4) : plafonner seul donne 100 à un hook de deux
        # mots, qui n'accroche rien. Le plancher est le p25 mesuré de la niche.
        score -= (plancher_mots - mots) * PENALITE_MOT_MANQUANT
        candidat.infractions.append(
            f"longueur : {mots} mots, sous le plancher de {plancher_mots} (p25 de la niche)")

    for formulation in patterns.proscrites_trouvees(texte):
        score -= PENALITE_PROSCRITE
        candidat.infractions.append(f"formulation proscrite : « {formulation} »")

    element = patterns.elements_cles.get(type_hook)
    if element:
        verificateur = VERIFICATEURS.get(element)
        if verificateur is None:
            candidat.infractions.append(
                f"élément clé « {element} » : aucun vérificateur mécanique — non vérifié")
        elif not verificateur(texte, patterns.lexiques.get(element, [])):
            score -= PENALITE_ELEMENT_ABSENT
            candidat.infractions.append(
                f"élément clé du type {type_hook} absent : {element}")

    candidat.score = max(0.0, score)
    return candidat


# --------------------------------------------------------------------------------------
# Génération et duel
# --------------------------------------------------------------------------------------

SCHEMA_CANDIDATS = {
    "type": "object",
    "properties": {"hooks": {"type": "array", "minItems": 1, "items": {
        "type": "object",
        "properties": {"text": {"type": "string"}, "on_screen_text": {"type": "string"},
                       "visual_intent": {"type": "string"}},
        "required": ["text", "on_screen_text", "visual_intent"]}}},
    "required": ["hooks"],
}

SCHEMA_DUEL = {
    "type": "object",
    "properties": {"winner": {"type": "integer"}, "why": {"type": "string"}},
    "required": ["winner", "why"],
}

SYSTEME_DUEL = (
    "You compare two opening lines of a YouTube video. You answer with one JSON object only."
)

GABARIT_DUEL = """Topic: "{sujet}"

Two openings of the same video, both of hook type {type_hook} ({definition}).

1: "{a}"
2: "{b}"

Which one makes a viewer keep watching past the third second?

Answer with this JSON object and nothing else:
{{"winner": 1 or 2, "why": "<at most 12 words>"}}

Judge on this order of priority: it opens on something concrete, it raises a question it does
not answer, it wastes no word on introducing itself."""


@dataclass
class Choix:
    """Ce que le tirage, la note et le duel ont décidé — recopié tel quel au manifeste."""

    type: str
    part: float
    candidats: list[Candidat]
    choisi: Candidat
    motif: str = ""

    def json_manifeste(self) -> dict[str, Any]:
        return {"hook_type": self.type,
                "hook_candidates": [c.json() for c in self.candidats],
                "hook_chosen": self.choisi.texte,
                "hook_choice_reason": self.motif}


def parts_apprises(niche: str, racine: Path | None = None) -> dict[str, float] | None:
    """Parts de `learned/weights.json → hooks.<niche>.parts`, ou `None` (repli référentiel).

    Les parts apprises ne peuvent qu'être le référentiel × des multiplicateurs bornés
    [0,7 ; 1,4] puis renormalisé : aucun type du référentiel ne tombe à zéro.
    """
    from factory.analytics import weights as wmod

    bloc = ((wmod.charger(racine) or {}).get("hooks") or {}).get(niche) or {}
    parts = bloc.get("parts") if bloc.get("changed") else None
    if not isinstance(parts, dict):
        return None
    propres = {str(t): float(p) for t, p in parts.items()
               if isinstance(p, (int, float)) and p > 0}
    return propres or None


def tirer_type(niche: str, seed: int, racine: Path | None = None) -> tuple[str, float]:
    """Tire le type de hook selon les parts de la niche (apprises si actives). Seedé."""
    import random

    parts = parts_apprises(niche, racine)
    if parts is None:
        return ref_module.tirer_type_hook(niche, seed, racine)
    productibles = ref_module.types_productibles(racine)
    retenus = {t: p for t, p in parts.items() if t in productibles}
    if not retenus:
        return ref_module.tirer_type_hook(niche, seed, racine)
    types = sorted(retenus)
    poids = [retenus[t] for t in types]
    tire = random.Random(seed).choices(types, weights=poids, k=1)[0]
    return tire, retenus[tire] / sum(poids)


def choisir(
    candidats: list[Candidat], type_hook: str, sujet: str, definition: str,
    seed: int = 0, racine: Path | None = None, trace: Any | None = None,
    duel: bool = True,
) -> tuple[Candidat, str]:
    """Trie par note, fait départager les deux meilleurs par le modèle, rend le gagnant.

    Le duel n'a lieu que si les deux meilleurs sont **tous deux acceptables** et séparés de
    moins de 20 points : en dessous, la note par règles a déjà tranché et l'appel serait payé
    pour rien. Un duel indisponible laisse le meilleur au classement des règles.
    """
    if not candidats:
        raise ValueError("aucun candidat de hook")
    classes = sorted(candidats, key=lambda c: -c.score)
    meilleur, second = classes[0], (classes[1] if len(classes) > 1 else None)
    if second is None or not duel or not second.acceptable \
            or meilleur.score - second.score >= 20.0:
        return meilleur, f"note par règles ({meilleur.score:.0f}/100)"
    try:
        donnees, _ = llm.generate_json(
            GABARIT_DUEL.format(sujet=sujet, type_hook=type_hook, definition=definition[:200],
                                a=meilleur.texte, b=second.texte),
            system=SYSTEME_DUEL, json_schema=SCHEMA_DUEL, max_tokens=120, temperature=0.3,
            seed=seed, etiquette="retention:hook:duel", trace=trace, racine=racine,
        )
    except Exception as erreur:  # noqa: BLE001 — message exact rapporté, jamais reformulé
        return meilleur, f"duel indisponible ({erreur}) — note par règles"
    gagnant = second if int(donnees.get("winner", 1)) == 2 else meilleur
    return gagnant, f"duel LLM : {str(donnees.get('why', ''))[:100]}"
