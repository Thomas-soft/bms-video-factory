"""Boucles ouvertes : où les planter, où les payer, et comment vérifier qu'elles le sont.

**Le défaut que ce module refuse.** Un script peut porter `open_loop: plant` et `payoff` dans
son JSON sans qu'une seule phrase promette ni ne tienne quoi que ce soit : l'étiquette est
posée par le code, le texte est écrit par le modèle, et rien ne les reliait. Le banc de
l'étape 15 comptait donc des boucles qui n'existaient que dans les métadonnées
(`open_loops_paid` sur `script.json`). Ici, une boucle n'est tenue que si :

1. le segment `plant` contient un **marqueur de promesse** mesuré sur le corpus
   (`patterns_<lang>.yaml → boucle.marqueurs_plantation`) ;
2. le segment `payoff`, qui vient **après**, contient un **marqueur de paiement** ;
3. un juge LLM court répond que le second répond bien à la promesse du premier.

Les deux premiers points sont mécaniques et gratuits ; le troisième coûte un appel de quelques
centaines de jetons par boucle et peut être sauté (`juge=False`) quand aucun modèle n'est
disponible — le verdict est alors `None`, jamais `True`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from factory import llm
from factory.core.models import Script
from factory.retention.patterns import Patterns

#: Rôles qui ne peuvent porter ni promesse ni paiement : la divulgation sponsor est
#: contractuelle, l'appel à l'action et la conclusion ferment la vidéo.
ROLES_RESERVES = frozenset({"sponsor", "cta", "conclusion"})


# --------------------------------------------------------------------------------------
# Planification
# --------------------------------------------------------------------------------------

def planifier(roles: Sequence[str], minimum: int = 2) -> list[str]:
    """Décide `plant` / `payoff` / `none` pour chaque segment, avant tout appel au LLM.

    Le prompt de l'étape 16 impose la plantation « à la fin du segment 1 ou 2 » : le hook
    plante la première boucle (c'est sa fonction même) et le segment suivant la seconde. Les
    paiements sont placés au milieu et avant la conclusion, jamais sur un rôle réservé.
    """
    n = len(roles)
    if n < 4:
        raise ValueError(f"{n} segment(s) : trop peu pour planter et payer {minimum} boucle(s)")
    boucles = ["none"] * n
    dernier = n - 1
    for index in range(min(minimum, n)):
        if roles[index] not in ROLES_RESERVES:
            boucles[index] = "plant"
    plants = [i for i, b in enumerate(boucles) if b == "plant"]

    cibles = [max(2, int(n * 0.55)), max(3, dernier - 2)]
    for cible in cibles:
        index = min(cible, dernier)
        while index >= 2 and (roles[index] in ROLES_RESERVES or boucles[index] != "none"):
            index -= 1
        if index >= 2 and index > min(plants, default=0):
            boucles[index] = "payoff"
    return boucles


# --------------------------------------------------------------------------------------
# Vérification
# --------------------------------------------------------------------------------------

@dataclass
class Boucle:
    """Une promesse et, si elle existe, son paiement."""

    plant_id: str
    payoff_id: str | None
    marqueurs_plant: list[str]
    marqueurs_payoff: list[str]
    #: Verdict du juge LLM. `None` = non jugé, jamais « réussi par défaut ».
    coherente: bool | None = None
    motif: str = ""

    @property
    def plantee(self) -> bool:
        """La promesse est-elle écrite, et pas seulement étiquetée ?"""
        return bool(self.marqueurs_plant)

    @property
    def payee(self) -> bool:
        """Le paiement existe-t-il, est-il marqué, et le juge ne l'a-t-il pas démenti ?"""
        return (self.payoff_id is not None and bool(self.marqueurs_payoff)
                and self.coherente is not False)


def apparier(script: Script, patterns: Patterns) -> list[Boucle]:
    """Apparie chaque `plant` au premier `payoff` qui le suit, et cherche les marqueurs.

    Un `payoff` placé avant tous les `plant` n'en paie aucun : l'ordre des segments fait foi,
    comme au banc (`factory/eval/metrics/structure.py`).
    """
    ordre = {segment.id: index for index, segment in enumerate(script.segments)}
    par_id = {segment.id: segment for segment in script.segments}
    plants = [s.id for s in script.segments if s.open_loop == "plant"]
    payoffs = [s.id for s in script.segments if s.open_loop == "payoff"]
    disponibles = sorted(payoffs, key=lambda i: ordre[i])

    boucles: list[Boucle] = []
    for plant_id in sorted(plants, key=lambda i: ordre[i]):
        payoff_id = next((p for p in disponibles if ordre[p] > ordre[plant_id]), None)
        if payoff_id is not None:
            disponibles.remove(payoff_id)
        texte_plant = par_id[plant_id].narration
        # La promesse se joue dans la **fin** du segment, pas dans son corps : c'est la
        # dernière phrase que le spectateur emporte. Le marqueur y est cherché en priorité,
        # puis dans tout le segment — une promesse posée plus tôt reste une promesse.
        marqueurs_plant = patterns.plante(_derniere_phrase(texte_plant)) or patterns.plante(
            texte_plant)
        marqueurs_payoff = (
            patterns.paie(_premiere_phrase(par_id[payoff_id].narration))
            or patterns.paie(par_id[payoff_id].narration)
        ) if payoff_id is not None else []
        boucles.append(Boucle(plant_id=plant_id, payoff_id=payoff_id,
                              marqueurs_plant=marqueurs_plant,
                              marqueurs_payoff=marqueurs_payoff))
    return boucles


_FIN = re.compile(r"(?<=[.!?…])\s+")


def _derniere_phrase(texte: str) -> str:
    phrases = [p for p in _FIN.split(texte.strip()) if p]
    return " ".join(phrases[-2:]) if phrases else texte


def _premiere_phrase(texte: str) -> str:
    phrases = [p for p in _FIN.split(texte.strip()) if p]
    return " ".join(phrases[:2]) if phrases else texte


# --------------------------------------------------------------------------------------
# Juge de cohérence
# --------------------------------------------------------------------------------------

SYSTEME_JUGE = (
    "You check whether a payoff answers a promise. You answer with one JSON object only."
)

GABARIT_JUGE = """A narrator made this promise:
"{promesse}"

Later in the same video, the narrator said:
"{paiement}"

Does the second passage deliver what the first one promised?

Answer with this JSON object and nothing else:
{{"answers": true or false, "why": "<at most 12 words>"}}

Rules:
- `true` only if the second passage gives the information the promise announced.
- Restating the promise, or changing the subject, is `false`.
- A partial but concrete answer is `true`."""

SCHEMA_JUGE = {
    "type": "object",
    "properties": {"answers": {"type": "boolean"},
                   "why": {"type": "string"}},
    "required": ["answers", "why"],
}

#: Extrait soumis au juge, en caractères. Au-delà, un 9B quantifié cesse de comparer.
EXTRAIT_MAX = 600


def juger(
    script: Script, boucles: list[Boucle], seed: int = 0, racine: Path | None = None,
    trace: Any | None = None,
) -> list[Boucle]:
    """Fait trancher la cohérence sémantique de chaque boucle par un appel LLM court.

    Modifie les boucles en place et les rend. Un appel qui échoue laisse `coherente = None` :
    l'absence de juge n'est pas un succès, et `verify` la rapporte comme telle.
    """
    par_id = {segment.id: segment for segment in script.segments}
    for boucle in boucles:
        if boucle.payoff_id is None:
            boucle.motif = "aucun paiement après cette promesse"
            continue
        promesse = _derniere_phrase(par_id[boucle.plant_id].narration)[-EXTRAIT_MAX:]
        paiement = _premiere_phrase(par_id[boucle.payoff_id].narration)[:EXTRAIT_MAX]
        try:
            donnees, _ = llm.generate_json(
                GABARIT_JUGE.format(promesse=promesse, paiement=paiement),
                system=SYSTEME_JUGE, json_schema=SCHEMA_JUGE, max_tokens=120,
                temperature=0.2, seed=seed, etiquette=f"retention:boucle:{boucle.plant_id}",
                trace=trace, racine=racine,
            )
        except Exception as erreur:  # noqa: BLE001 — le message exact est rapporté tel quel
            boucle.coherente = None
            boucle.motif = f"juge indisponible : {erreur}"
            continue
        boucle.coherente = bool(donnees.get("answers"))
        boucle.motif = str(donnees.get("why", ""))[:120]
    return boucles


def resume(boucles: list[Boucle]) -> tuple[int, int]:
    """`(plantées, payées)` au sens de ce module : marqueurs trouvés, juge non démenti."""
    return sum(1 for b in boucles if b.plantee), sum(1 for b in boucles if b.payee)
