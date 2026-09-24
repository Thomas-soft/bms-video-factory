"""Ruptures de rythme : une toutes les N secondes, N = 4 × rythme de coupe cible.

**Pourquoi 4 ×.** Le rythme de coupe est un fait visuel (une image change) ; la rupture est un
fait éditorial (le sujet change, une question est posée, un chiffre tombe). Les confondre
donnerait une rupture tous les 6 s sur `science_pop`, c'est-à-dire du hachis. Le facteur 4 vient
du prompt de l'étape 10 et la borne [20, 45] s de l'étape 16 : en deçà de 20 s la rupture n'est
plus une rupture, au-delà de 45 s le creux du milieu se réinstalle.

**Ce que le module ne fait pas.** Il ne réécrit rien : il pose un marqueur sur un segment, et
c'est `script.py` qui demande au LLM d'honorer ce marqueur, `shotlist.py` qui en fait une coupe
forcée (`plans_de_fenetre`, ancre). Le module n'a donc besoin que des durées estimées.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from factory.core.models import Interrupt

#: Multiplicateur du rythme de coupe qui donne la cadence des ruptures (prompt étape 10).
FACTEUR_RUPTURE = 4
#: Bornes de la cadence, en secondes (prompt étape 16).
INTERVALLE_MIN_S = 20.0
INTERVALLE_MAX_S = 45.0

#: Types de rupture, dans l'ordre du prompt de l'étape 16. `silence` reste accepté par le
#: modèle de données (runs antérieurs au 18/09/2026) mais n'est plus tiré : une pause n'est
#: pas une rupture d'attention, c'est une respiration — elle relève du mixage (défaut n° 2 de
#: l'étape 13.2), pas de l'écriture.
TYPES = ("question", "chiffre", "changement_de_plan", "mini_recit")

#: Rôles qui ne portent jamais de rupture : le hook en est une à lui seul, la divulgation
#: sponsor est contractuelle et la conclusion ne se coupe pas en deux.
ROLES_SANS_RUPTURE = frozenset({"hook", "sponsor", "conclusion"})

#: Marge minimale entre une rupture et les bords de son segment : en deçà, `shotlist.py`
#: écarte l'ancre (`DUREE_MIN_S`) et la rupture est posée pour rien.
MARGE_BORD_S = 1.5


def intervalle_s(cut_rhythm_target_s: float) -> float:
    """Cadence des ruptures pour un rythme de coupe donné, bornée à [20, 45] s."""
    brut = FACTEUR_RUPTURE * float(cut_rhythm_target_s)
    return min(INTERVALLE_MAX_S, max(INTERVALLE_MIN_S, brut))


@dataclass
class Plan:
    """Ce que la planification a décidé, pour le manifeste et pour les tests."""

    #: Une entrée par segment, `None` quand le segment n'en porte pas.
    par_segment: list[Interrupt | None]
    #: Instants absolus des ruptures posées, en secondes depuis le début de la vidéo.
    instants_s: list[float]
    intervalle_s: float
    #: Cadences visées qu'aucun segment n'a pu porter (segment trop court, rôle exclu).
    manquees: list[float]

    @property
    def n(self) -> int:
        """Nombre de ruptures effectivement posées."""
        return len(self.instants_s)

    @property
    def ecart_max_s(self) -> float | None:
        """Plus grand intervalle entre deux ruptures, bords de la vidéo compris."""
        if not self.instants_s:
            return None
        return max(b - a for a, b in zip([0.0, *self.instants_s], self.instants_s))


def planifier(
    durees_s: Sequence[float], roles: Sequence[str], cadence_s: float, seed: int,
) -> Plan:
    """Pose une rupture par tranche de `cadence_s`, une au maximum par segment.

    Le modèle de données n'accepte qu'une rupture par segment (`ScriptSegment.interrupt`) :
    quand deux cadences tombent dans le même segment, la seconde est comptée `manquee` plutôt
    que perdue en silence — c'est ce que `verify` lit pour dire que le script est trop peu
    découpé pour porter le rythme demandé.
    """
    if len(durees_s) != len(roles):
        raise ValueError(f"{len(durees_s)} durée(s) pour {len(roles)} rôle(s)")
    debuts: list[float] = []
    horloge = 0.0
    for duree in durees_s:
        debuts.append(horloge)
        horloge += float(duree)
    total = horloge

    alea = random.Random(seed)
    par_segment: list[Interrupt | None] = [None] * len(durees_s)
    instants: list[float] = []
    manquees: list[float] = []
    precedent: str | None = None

    cible = cadence_s
    while cible < total:
        index = _segment_contenant(debuts, durees_s, cible)
        if (index is None or par_segment[index] is not None
                or roles[index] in ROLES_SANS_RUPTURE
                or float(durees_s[index]) < 2 * MARGE_BORD_S):
            manquees.append(round(cible, 1))
            cible += cadence_s
            continue
        relative = _caler(cible - debuts[index], float(durees_s[index]))
        type_rupture = _tirer_type(alea, precedent)
        precedent = type_rupture
        par_segment[index] = Interrupt(type=type_rupture, at_s_relative=round(relative, 1))
        instants.append(round(debuts[index] + relative, 1))
        cible += cadence_s

    return Plan(par_segment=par_segment, instants_s=instants, intervalle_s=cadence_s,
                manquees=manquees)


def _segment_contenant(debuts: list[float], durees: Sequence[float], instant: float) -> int | None:
    """Index du segment qui contient `instant`, ou `None` au-delà de la fin."""
    for index, debut in enumerate(debuts):
        if debut <= instant < debut + float(durees[index]):
            return index
    return None


def _caler(relative: float, duree: float) -> float:
    """Ramène la rupture dans [MARGE_BORD_S, durée − MARGE_BORD_S]."""
    haut = max(MARGE_BORD_S, duree - MARGE_BORD_S)
    return min(haut, max(MARGE_BORD_S, relative))


def _tirer_type(alea: random.Random, precedent: str | None) -> str:
    """Tire un type, jamais deux fois le même d'affilée : c'est la répétition qui use."""
    choix = [t for t in TYPES if t != precedent] or list(TYPES)
    return alea.choice(choix)


#: Ce que le LLM doit écrire pour honorer chaque type, en anglais (langue de production).
CONSIGNES_EN = {
    "question": "end this segment on a direct question to the viewer, answered in the next one",
    "chiffre": "open this segment on a figure taken from the fact list, stated out loud",
    "changement_de_plan": "start this segment on a new setting or a new object, named in its "
                          "first sentence",
    "mini_recit": "open this segment on a two-sentence concrete scene (one person or one place, "
                  "one moment), then return to the explanation",
    "silence": "leave a beat: one short sentence on its own before the segment continues",
}


def consigne(type_rupture: str) -> str:
    """Consigne d'écriture du type de rupture, pour le gabarit de narration."""
    return CONSIGNES_EN.get(type_rupture, CONSIGNES_EN["changement_de_plan"])
