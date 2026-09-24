"""Famille « parole » — le débit de narration et la respiration, depuis `words.json`.

Le débit se mesure comme le registre le mesure (`REFERENTIEL.md` § 6.3) : mots ÷ durée parlée,
sur la transcription entière. Prendre la durée de la vidéo au dénominateur donnerait un débit
artificiellement bas dès qu'il y a une pause — deux grandeurs différentes ne se comparent pas.

La respiration est ici et non dans la famille audio parce que c'est la **narration** qui ne
respire pas : défaut n° 2 de l'étape 13.2, mesuré — 90,1 % de parole, aucun silence ≥ 0,4 s en
douze minutes. `silencedetect` mesure le fichier mixé ; les blancs entre mots de `words.json`
mesurent le débit lui-même, lit musical ou pas.
"""

from __future__ import annotations

from typing import Any

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc


def mesurer(contexte: ContexteQc) -> Famille:
    """Mots/min face au référentiel de la niche, et pauses de narration par minute."""
    famille = Famille("parole", poids=contexte.qc.poids.get("parole", 5))
    donnees = contexte.words
    if not donnees or not donnees.get("words"):
        famille.mesures.append(Mesure(
            nom="speech_rate", valeur=None, unite="mots/min", cible=None,
            source="words.json", origine_cible=base.REGISTRE, score=None, statut="skipped",
            note="words.json absent ou vide : ni débit ni respiration mesurables",
        ))
        return famille

    mots: list[dict[str, Any]] = donnees["words"]
    debut = min(float(m["start_s"]) for m in mots)
    fin = max(float(m["end_s"]) for m in mots)
    parle = _duree_parlee(mots)
    etendue = max(fin - debut, 1e-6)

    bloc = contexte.niche.get("mots_par_minute", {})
    cible = bloc.get("mediane")
    seuil = contexte.seuil("speech_rate")
    debit = len(mots) / etendue * 60.0
    if cible is None:
        famille.mesures.append(Mesure(
            nom="speech_rate", valeur=round(debit, 1), unite="mots/min", cible=None,
            source="words.json (mots ÷ étendue parlée)", origine_cible=base.REGISTRE,
            score=None, poids=2, statut="skipped", note="pas de débit mesuré pour cette niche",
        ))
    else:
        cible = float(cible)
        score = base.score_cible(
            debit, cible, float(seuil.get("tolerance", 0.15)), float(seuil.get("plage", 0.45))
        )
        famille.mesures.append(Mesure(
            nom="speech_rate", valeur=round(debit, 1), unite="mots/min", cible=round(cible, 1),
            source="words.json (mots ÷ étendue parlée, méthode du registre)",
            origine_cible=f"{base.REGISTRE} — mots_par_minute.mediane (n={bloc.get('n')})",
            score=score, poids=1, statut=base.statut_depuis(score),
            note=(
                f"fourchette de la niche p25 {bloc.get('p25')} – p75 {bloc.get('p75')}. "
                "**Partiellement acquis par construction** (objection C2) : cette médiane "
                "dimensionne déjà le script et la voix. Ce qui reste mesuré est la dérive du "
                "TTS, du rognage de silence et de l'atempo. Poids réduit à 1 pour cette raison"
            ),
        ))

    # -- respiration -------------------------------------------------------------------------
    seuil_r = contexte.seuil("respiration")
    plancher = float(contexte.mesure_param("parole").get("pause_min_s", 0.4))
    pauses = _pauses(mots, plancher)
    par_minute = len(pauses) / (etendue / 60.0)
    minimum = float(seuil_r.get("min", 2.0))
    score_r = base.score_min(par_minute, minimum, float(seuil_r.get("zero", 0.0)))
    famille.mesures.append(Mesure(
        nom="respiration", valeur=round(par_minute, 2), unite=f"pauses ≥ {plancher:g} s / min",
        cible=minimum, source="words.json (blancs entre mots consécutifs)",
        origine_cible=f"{base.DECISION} — défaut n° 2 de l'étape 13.2, aucune mesure de registre",
        score=score_r, poids=2, statut=base.statut_depuis(score_r),
        note=(
            f"{len(pauses)} pause(s) en {etendue / 60:.1f} min ; part parlée "
            f"{parle / etendue:.1%} ; plus longue pause {max((p for p in pauses), default=0.0):.2f} s"
        ),
    ))

    fenetre = float(contexte.mesure_param("parole").get("fenetre_debit_s", 30.0))
    p90 = _debit_p90(mots, fenetre)
    famille.mesures.append(Mesure(
        nom="speech_rate_p90", valeur=None if p90 is None else round(p90, 1), unite="mots/min",
        cible=None, source=f"words.json — p90 des fenêtres glissantes de {fenetre:g} s",
        origine_cible=(
            "mesure sans cible : le registre mesure un débit GLOBAL, comparer un p90 à une "
            "médiane globale serait une faute de méthode. Sert aux étapes 16 et 26."
        ),
        score=None, statut="skipped",
        note="repère les passages débités, que la moyenne globale efface",
    ))
    famille.mesures.append(Mesure(
        nom="speech_share", valeur=round(parle / etendue, 3), unite="part",
        cible=None, source="words.json", origine_cible="mesure sans cible — sert à l'étape 26",
        score=None, statut="skipped", note="part du temps où un mot est prononcé",
    ))
    return famille


def _debit_p90(mots: list[dict[str, Any]], fenetre_s: float, pas_s: float = 5.0) -> float | None:
    """p90 du débit instantané, mesuré sur des fenêtres glissantes.

    Le débit global lisse tout : une vidéo qui débite pendant deux minutes puis traîne rend la
    même moyenne qu'une vidéo régulière. Le p90 dit ce que le spectateur encaisse au pire.
    """
    if not mots:
        return None
    debuts = sorted(float(m["start_s"]) for m in mots)
    fin = max(float(m["end_s"]) for m in mots)
    if fin - debuts[0] < fenetre_s:
        return None
    import bisect

    debits = []
    instant = debuts[0]
    while instant + fenetre_s <= fin:
        gauche = bisect.bisect_left(debuts, instant)
        droite = bisect.bisect_left(debuts, instant + fenetre_s)
        debits.append((droite - gauche) * 60.0 / fenetre_s)
        instant += pas_s
    if not debits:
        return None
    debits.sort()
    return debits[min(len(debits) - 1, int(0.90 * (len(debits) - 1)))]


def _duree_parlee(mots: list[dict[str, Any]]) -> float:
    """Somme des intervalles où un mot est prononcé, fusion des chevauchements."""
    intervalles = sorted(
        (float(m["start_s"]), float(m["end_s"])) for m in mots if float(m["end_s"]) > float(m["start_s"])
    )
    total, courant_debut, courant_fin = 0.0, None, None
    for debut, fin in intervalles:
        if courant_fin is None or debut > courant_fin:
            if courant_fin is not None:
                total += courant_fin - courant_debut
            courant_debut, courant_fin = debut, fin
        else:
            courant_fin = max(courant_fin, fin)
    if courant_fin is not None:
        total += courant_fin - courant_debut
    return total


def _pauses(mots: list[dict[str, Any]], plancher_s: float) -> list[float]:
    """Blancs entre mots consécutifs d'au moins `plancher_s`."""
    ordonnes = sorted(mots, key=lambda m: float(m["start_s"]))
    blancs = []
    for precedent, suivant in zip(ordonnes, ordonnes[1:]):
        blanc = float(suivant["start_s"]) - float(precedent["end_s"])
        if blanc >= plancher_s:
            blancs.append(blanc)
    return blancs
