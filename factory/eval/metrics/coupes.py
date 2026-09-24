"""Famille « coupes » — le rythme **perçu**, mesuré sur le fichier livré.

Le banc ne lit pas `shotlist.json` pour compter les plans : il détecte les coupes visibles dans
`final.mp4`. Les deux divergent, et c'est le point (étape 13.1, mesuré) — deux plans servis par
la même image ne produisent aucune coupe visible. Le spectateur voit ce que PySceneDetect voit,
pas ce que la liste de plans déclare.

Cinq mesures : le rythme médian, la dispersion (p10/p90), les plans trop longs, le rythme du
hook sur 15 s, et le nombre de plans. La dispersion est notée à part de la médiane parce qu'une
médiane juste peut couvrir une alternance de plans de 1 s et de 20 s.
"""

from __future__ import annotations

import statistics

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc


def _cible_rythme(contexte: ContexteQc) -> tuple[float | None, str, bool]:
    """Cible de rythme de coupe, dans l'ordre de lecture imposé par le référentiel.

    `cible_montage` → `cible` → `fallback_provisoire_s`. Le repli n'est **pas** une cible
    (`REFERENTIEL.md` § 2) : quand c'est lui qui sert, la mesure sort `skipped`.
    """
    bloc = contexte.niche.get("rythme_coupe_s", {})
    for champ in ("cible_montage", "cible"):
        valeur = bloc.get(champ)
        if valeur is not None:
            return float(valeur), f"{base.REGISTRE} — rythme_coupe_s.{champ}", False
    repli = bloc.get("fallback_provisoire_s")
    if repli is not None:
        return float(repli), f"{base.REGISTRE} — fallback_provisoire_s (a_mesurer)", True
    return None, f"{base.REGISTRE} — aucune valeur", True


def mesurer(contexte: ContexteQc) -> Famille:
    """Rythme, dispersion, plans trop longs et rythme du hook, sur les plans détectés."""
    famille = Famille("coupes", poids=contexte.qc.poids.get("coupes", 25))
    cible, origine, a_mesurer = _cible_rythme(contexte)
    scenes = contexte.scenes
    durees = [fin - debut for debut, fin in scenes if fin > debut]
    seuil = contexte.seuil("cut_rhythm")
    params = contexte.mesure_param("coupes")
    source = f"PySceneDetect ContentDetector seuil {params.get('seuil_contentdetector', 27.0)}"

    if not durees:
        famille.mesures.append(Mesure(
            nom="cut_rhythm", valeur=None, unite="s/plan", cible=cible, source=source,
            origine_cible=origine, score=None, statut="skipped",
            note="aucun plan détecté : mesure impossible, pas de note",
        ))
        return famille

    median = statistics.median(durees)
    p10 = _percentile(durees, 0.10)
    p90 = _percentile(durees, 0.90)
    tolerance = float(seuil.get("tolerance", 0.15))
    plage = float(seuil.get("plage", 0.60))

    # -- rythme médian ------------------------------------------------------------------
    if cible is None or a_mesurer:
        famille.mesures.append(Mesure(
            nom="cut_rhythm", valeur=round(median, 2), unite="s/plan", cible=cible,
            source=source, origine_cible=origine, score=None, poids=3, statut="skipped",
            note="cible marquée a_mesurer : mesurée, non notée (REFERENTIEL.md § 2)",
        ))
    else:
        score = base.score_cible(median, cible, tolerance, plage)
        famille.mesures.append(Mesure(
            nom="cut_rhythm", valeur=round(median, 2), unite="s/plan", cible=round(cible, 2),
            source=source, origine_cible=origine, score=score, poids=3,
            statut=base.statut_depuis(score),
            note=f"{len(scenes)} plans détectés sur {contexte.duree_s:.0f} s",
        ))

    # -- dispersion : mesurée, PAS notée ---------------------------------------------------
    # Objection B3 du contradicteur, retenue : le registre ne contient aucun p90/p10 — le
    # tableau P9 ne donne qu'une médiane par chaîne et n'est pas recalculable ici
    # (`REFERENTIEL.md` § 6.5). Un seuil de 3,0 n'aurait donc reposé sur rien, et les deux
    # seules valeurs mesurées de ce projet valent 4,33 et 5,07 : il aurait puni les deux runs
    # au nom d'une norme inventée. La mesure est publiée, sa note attend l'étape 26.
    etendue = p90 / p10 if p10 > 0 else float("inf")
    famille.mesures.append(Mesure(
        nom="cut_dispersion", valeur=round(etendue, 2), unite="p90/p10",
        cible=None, source=source,
        origine_cible="aucune — seuil non fondé sur une mesure, noté à partir de l'étape 26",
        score=None, poids=1, statut="skipped",
        note=f"p10 {p10:.2f} s · p90 {p90:.2f} s — une médiane juste peut cacher l'alternance",
    ))

    # -- plans trop longs (bloquant) ------------------------------------------------------
    # Deux objections du contradicteur, retenues toutes les deux.
    # B1 : le contrôle s'exécutait même quand `cut_rhythm` sortait `skipped`, c'est-à-dire
    #      contre le **repli provisoire de 7,8 s** que le référentiel refuse comme cible. Il est
    #      maintenant conditionné à une cible réelle.
    # B2 : bloquer sur le *nombre* de plans longs est trop brutal — `cible_montage` est déjà
    #      obtenue en retirant du corpus les chaînes à plans > 3× leur médiane, et un seul plan
    #      long suffisait à refuser une vidéo. Le bloquant porte sur la **part de durée** que
    #      ces plans occupent ; le nombre reste dans la note.
    if cible is not None and not a_mesurer:
        facteur = float(seuil.get("facteur_plan_long", 3.0))
        limite = cible * facteur
        longs = [d for d in durees if d > limite]
        part_longue = sum(longs) / contexte.duree_s if contexte.duree_s else 0.0
        maximum = float(seuil.get("part_longue_max", 0.10))
        bloquante = float(seuil.get("part_longue_bloquante", 0.25))
        score_longs = base.score_max(
            part_longue, maximum, float(seuil.get("part_longue_zero", 0.40))
        )
        famille.mesures.append(Mesure(
            nom="cut_long_shots", valeur=round(part_longue, 3), unite="part de la durée",
            cible=maximum, source=source,
            origine_cible=f"{base.DECISION} — plans au-delà de {facteur:g}× la cible de niche",
            score=score_longs, poids=2, bloquant=True,
            statut="fail" if part_longue > bloquante else base.statut_depuis(score_longs),
            note=(
                f"{len(longs)} plan(s) au-delà de {limite:.1f} s occupent "
                f"{part_longue:.1%} de la vidéo ; bloquant au-delà de {bloquante:.0%}"
                + (f" ; le plus long : {max(longs):.1f} s" if longs else "")
            ),
        ))

    # -- rythme du hook -------------------------------------------------------------------
    fenetre = float(params.get("fenetre_hook_s", 15.0))
    dans_hook = [d for (debut, _fin), d in zip(scenes, durees) if debut < fenetre]
    facteur_hook = float(contexte.niche.get("rythme_coupe_s", {}).get("facteur_hook") or 0.7)
    if cible is None or a_mesurer or not dans_hook:
        famille.mesures.append(Mesure(
            nom="cut_rhythm_hook", valeur=round(statistics.median(dans_hook), 2) if dans_hook
            else None,
            unite="s/plan", cible=None, source=source, origine_cible=origine,
            score=None, poids=2, statut="skipped",
            note=f"pas de cible de rythme notable sur les {fenetre:.0f} premières secondes",
        ))
    else:
        cible_hook = cible * facteur_hook
        median_hook = statistics.median(dans_hook)
        # Couper **plus vite** que la cible du hook est la consigne, pas un défaut : la note ne
        # pénalise que le dépassement. Le plancher est tenu par `cut_dispersion` et par le
        # rythme médian, qui, eux, sont symétriques.
        score_hook = base.score_max(
            median_hook, cible_hook, cible_hook * float(seuil.get("plage_hook", 2.5))
        )
        famille.mesures.append(Mesure(
            nom="cut_rhythm_hook", valeur=round(median_hook, 2), unite="s/plan",
            cible=round(cible_hook, 2), source=source,
            origine_cible=f"{origine} × facteur_hook {facteur_hook}",
            score=score_hook, poids=2, statut=base.statut_depuis(score_hook),
            note=f"{len(dans_hook)} plan(s) dans les {fenetre:.0f} premières secondes",
        ))

    famille.mesures.append(Mesure(
        nom="n_scenes", valeur=len(scenes), unite="plans", cible=None, source=source,
        origine_cible="mesure sans cible — sert à l'étape 26", score=None, statut="skipped",
        note="nombre de plans **visibles**, à ne pas confondre avec n_shots de shotlist.json",
    ))
    # Objection D2, retenue : `REFERENTIEL.json → ruptures_s` porte « faite au banc (étape 15) »
    # et le champ est vide. Le banc la mesure donc, sans la noter : la cible est fixée à
    # l'étape 16, et noter avant d'avoir une cible serait inventer une norme.
    famille.mesures.append(_cadence_par_minute(contexte, scenes, source))
    return famille


def _cadence_par_minute(contexte: ContexteQc, scenes, source: str) -> Mesure:
    """Rythme de coupe par tranche de 60 s, et sa pente. Mesuré, jamais noté."""
    tranche = 60.0
    n_tranches = max(1, int(contexte.duree_s // tranche))
    par_tranche = [0] * n_tranches
    for debut, _fin in scenes:
        index = min(int(debut // tranche), n_tranches - 1)
        par_tranche[index] += 1
    rythmes = [round(tranche / n, 2) if n else None for n in par_tranche]
    connus = [(i, r) for i, r in enumerate(rythmes) if r is not None]
    pente = None
    if len(connus) >= 2:
        moyenne_x = sum(i for i, _ in connus) / len(connus)
        moyenne_y = sum(r for _, r in connus) / len(connus)
        variance = sum((i - moyenne_x) ** 2 for i, _ in connus)
        if variance:
            pente = round(
                sum((i - moyenne_x) * (r - moyenne_y) for i, r in connus) / variance, 3
            )
    return Mesure(
        nom="cut_rhythm_by_minute", valeur=pente, unite="s/plan gagnée par minute",
        cible=None, source=source,
        origine_cible=(
            f"{base.REGISTRE} — ruptures_s porte a_mesurer, cible fixée à l'étape 16"
        ),
        score=None, statut="skipped",
        note=f"rythme par tranche de 60 s : {rythmes} ; pente positive = la vidéo ralentit",
    )


def _percentile(valeurs: list[float], part: float) -> float:
    """Percentile par interpolation linéaire, sans dépendance."""
    ordonnees = sorted(valeurs)
    if len(ordonnees) == 1:
        return ordonnees[0]
    position = part * (len(ordonnees) - 1)
    bas = int(position)
    haut = min(bas + 1, len(ordonnees) - 1)
    return ordonnees[bas] + (ordonnees[haut] - ordonnees[bas]) * (position - bas)
