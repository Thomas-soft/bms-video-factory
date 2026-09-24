"""Famille « variété » — chaque plan apporte-t-il une image nouvelle ?

Mesure directe du défaut n° 1 de l'étape 13.2 : sur le run `rtmk`, **36 images distinctes en
12 minutes, l'une d'elles servie 22 fois**, 71 % des plans servis par une image déjà vue. Le
rythme de coupe, lui, était bon — c'est exactement le cas qu'une note de rythme seule laisse
passer.

**Les images sont prises aux plans PLANIFIÉS (`shotlist.json`), pas aux plans détectés.** Mesurer
la variété entre plans détectés serait circulaire : un plan n'est détecté que parce qu'il diffère
du précédent, et la mesure rendrait toujours un bon chiffre. C'est la différence entre « les
coupes visibles sont franches » (vrai, et sans intérêt) et « le montage se répète » (la question).

Méthode : une image au milieu de chaque plan planifié, `phash` 64 bits, distance de Hamming.
Échelle mesurée à l'étape 15 : deux images franchement différentes rendent 22 à 36 sur 64 ;
« quasi identique » commence à 8. Le hachage perceptuel ignore l'échelle, donc un zoom sur la
même image reste proche — comportement voulu, c'est bien la même image.
"""

from __future__ import annotations

import statistics

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc


def mesurer(contexte: ContexteQc) -> Famille:
    """Distance perceptuelle entre plans consécutifs, redondance, et images distinctes."""
    famille = Famille("variete", poids=contexte.qc.poids.get("variete", 10))
    params = contexte.mesure_param("variete")
    instants, origine = _instants(contexte)
    if len(instants) < 2:
        famille.mesures.append(Mesure(
            nom="visual_variety", valeur=None, unite="distance de Hamming", cible=None,
            source="imagehash phash", origine_cible=base.DECISION, score=None,
            statut="skipped", note="moins de deux plans à comparer",
        ))
        return famille

    empreintes = _empreintes(contexte, instants, int(params.get("taille_hash", 8)))
    valides = [e for e in empreintes if e is not None]
    # `imagehash` rend une distance numpy : sans le `int`, `json.dump` refuse le résultat.
    distances = [
        int(a - b) for a, b in zip(empreintes, empreintes[1:]) if a is not None and b is not None
    ]
    if not distances:
        famille.mesures.append(Mesure(
            nom="visual_variety", valeur=None, unite="distance de Hamming", cible=None,
            source="imagehash phash", origine_cible=base.DECISION, score=None,
            statut="skipped", note="aucune image extraite",
        ))
        return famille

    seuil_distance = contexte.seuil("visual_variety")
    seuil_redondance = contexte.seuil("visual_redundancy")
    seuil_distinct = contexte.seuil("visual_distinct")
    plancher = float(params.get("distance_quasi_identique", 8))
    source = (
        f"imagehash phash {params.get('taille_hash', 8)} bits, 1 image par {origine}"
    )

    median = statistics.median(distances)
    minimum = float(seuil_distance.get("min", 20.0))
    score = base.score_min(median, minimum, float(seuil_distance.get("zero", 4.0)))
    famille.mesures.append(Mesure(
        nom="visual_variety", valeur=round(median, 1), unite="distance de Hamming (0-64)",
        cible=minimum, source=source,
        origine_cible=f"{base.DECISION} — défaut n° 1 de l'étape 13.2, aucune mesure de registre",
        score=score, poids=2, statut=base.statut_depuis(score),
        note=f"{len(distances)} paires consécutives ; « quasi identique » ≤ {plancher:g}",
    ))

    quasi = [d for d in distances if d <= plancher]
    part = len(quasi) / len(distances)
    maximum = float(seuil_redondance.get("max", 0.15))
    score_r = base.score_max(part, maximum, float(seuil_redondance.get("zero", 0.60)))
    famille.mesures.append(Mesure(
        nom="visual_redundancy", valeur=round(part, 3), unite="part des paires",
        cible=maximum, source=source,
        origine_cible=f"{base.DECISION} — défaut n° 1 de l'étape 13.2",
        score=score_r, poids=2, statut=base.statut_depuis(score_r),
        note=(
            f"{len(quasi)}/{len(distances)} paires consécutives quasi identiques — un plan qui "
            "succède à la même image ne se voit pas comme une coupe"
        ),
    ))

    famille.mesures.append(_redondance_des_coupes(contexte, params, plancher))

    distinctes = _compter_distinctes(valides, plancher)
    ratio = distinctes / len(valides)
    minimum_d = float(seuil_distinct.get("min", 0.60))
    score_d = base.score_min(ratio, minimum_d, float(seuil_distinct.get("zero", 0.15)))
    famille.mesures.append(Mesure(
        nom="visual_distinct_ratio", valeur=round(ratio, 3), unite="images distinctes / plans",
        cible=minimum_d, source=source,
        origine_cible=(
            f"{base.DECISION} — mesure exacte du défaut n° 1 de l'étape 13.2 "
            "(36 images distinctes pour 124 plans = 0,29)"
        ),
        score=score_d, poids=3, statut=base.statut_depuis(score_d),
        note=(
            f"{distinctes} image(s) distincte(s) pour {len(valides)} plan(s) ; deux plans sont "
            f"« la même image » si leur distance phash est ≤ {plancher:g}"
        ),
    ))
    return famille


def _redondance_des_coupes(contexte: ContexteQc, params: dict, plancher: float) -> Mesure:
    """Part des coupes **visibles** qui ne changent pas l'image.

    Objection A2 du contradicteur, retenue : `coupes` lit le fichier livré, `variete`
    échantillonne les plans planifiés. Ajouter des coupes à l'intérieur d'un plan planifié
    faisait donc monter `cut_rhythm` sans rien coûter à la variété — un montage qui hache
    gagnait des points. Cette mesure ferme le passage : une coupe qui ne change pas l'image
    y est comptée. Ce n'est pas circulaire — deux plans détectés peuvent porter la même image,
    la coupe ayant été vue sur un texte, un cartouche ou un mouvement.
    """
    seuil = contexte.seuil("cut_redundancy")
    scenes = contexte.scenes
    if len(scenes) < 2:
        return Mesure(
            nom="cut_redundancy", valeur=None, unite="part des coupes", cible=None,
            source="imagehash phash", origine_cible=base.DECISION, score=None, poids=1,
            statut="skipped", note="moins de deux plans détectés",
        )
    instants = [(debut + fin) / 2.0 for debut, fin in scenes]
    empreintes = _empreintes(
        contexte, instants, int(params.get("taille_hash", 8)), sous_dossier="coupes"
    )
    distances = [
        int(a - b) for a, b in zip(empreintes, empreintes[1:]) if a is not None and b is not None
    ]
    if not distances:
        return Mesure(
            nom="cut_redundancy", valeur=None, unite="part des coupes", cible=None,
            source="imagehash phash", origine_cible=base.DECISION, score=None, poids=1,
            statut="skipped", note="aucune image extraite",
        )
    vaines = [d for d in distances if d <= plancher]
    part = len(vaines) / len(distances)
    maximum = float(seuil.get("max", 0.10))
    score = base.score_max(part, maximum, float(seuil.get("zero", 0.50)))
    return Mesure(
        nom="cut_redundancy", valeur=round(part, 3), unite="part des coupes",
        cible=maximum, source="imagehash phash, 1 image par plan détecté",
        origine_cible=f"{base.DECISION} — anti-artefact : une coupe doit changer l'image",
        score=score, poids=1, statut=base.statut_depuis(score),
        note=f"{len(vaines)}/{len(distances)} coupe(s) laissent l'image inchangée",
    )


def _instants(contexte: ContexteQc) -> tuple[list[float], str]:
    """Milieu de chaque plan planifié ; à défaut de shotlist, milieu de chaque plan détecté."""
    shotlist = contexte.shotlist
    if shotlist is not None:
        return (
            [s.start_s + s.duration_s / 2.0 for s in shotlist.shots], "plan planifié"
        )
    return (
        [(debut + fin) / 2.0 for debut, fin in contexte.scenes], "plan détecté (shotlist absente)"
    )


def _empreintes(
    contexte: ContexteQc, instants: list[float], taille: int, sous_dossier: str = "variete"
):
    """`phash` d'une image prise à chaque instant."""
    import imagehash
    from PIL import Image

    dossier = contexte.dossier_travail / sous_dossier
    empreintes = []
    for index, instant in enumerate(instants):
        chemin = base.extraire_image(
            contexte.video, min(instant, max(0.0, contexte.duree_s - 0.05)),
            dossier / f"plan_{index:04d}.jpg", largeur=320,
        )
        if not chemin.exists():
            empreintes.append(None)
            continue
        with Image.open(chemin) as image:
            empreintes.append(imagehash.phash(image, hash_size=taille))
    return empreintes


def _compter_distinctes(empreintes: list, plancher: float) -> int:
    """Nombre de groupes d'images, une image rejoignant le premier groupe assez proche.

    Regroupement glouton, sans matrice complète : sur 124 plans, la comparaison exhaustive
    coûterait 7 626 distances pour un résultat que le premier représentant donne déjà.
    """
    representants: list = []
    for empreinte in empreintes:
        if not any(int(empreinte - reference) <= plancher for reference in representants):
            representants.append(empreinte)
    return len(representants)
