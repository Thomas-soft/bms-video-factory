"""Famille « lisibilité » — taille du texte, contraste réel, nombre de mots à l'écran.

Deux des trois mesures viennent des **paramètres de rendu** et non de l'image : la taille du
texte est une constante du moteur de style et la taille des sous-titres un champ de la charte.
Les lire là est plus juste que de les retrouver par OCR — et c'est aussi la limite de la mesure,
consignée dans `docs/QC.md` : elles vérifient ce que le pipeline a **demandé**, pas ce que
l'encodeur a rendu. Le contraste, lui, est mesuré sur les images extraites, parce qu'un texte
blanc sur cartouche translucide dépend de l'image qui est dessous.

Méthode du contraste : seuillage d'Otsu sur la luminance du bandeau de texte, luminance
relative WCAG 2.1 des deux classes, rapport `(L1 + 0,05) / (L2 + 0,05)`. Aucun OCR : tesseract
coûterait une seconde par image pour retrouver une position que la charte connaît déjà.
"""

from __future__ import annotations

import importlib
import statistics

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc

#: Hauteur de référence du contrat de rendu (`factory/video.py`).
HAUTEUR = 1080


def mesurer(contexte: ContexteQc) -> Famille:
    """Taille relative du texte, contraste WCAG mesuré, densité de mots à l'écran."""
    famille = Famille("lisibilite", poids=contexte.qc.poids.get("lisibilite", 10))
    famille.mesures.append(_taille_texte(contexte))
    famille.mesures.append(_contraste(contexte))
    famille.mesures.append(_mots_a_l_ecran(contexte))
    return famille


def _taille_moteur(contexte: ContexteQc) -> tuple[int | None, str]:
    """Taille du texte incrusté, lue dans le moteur de style de la chaîne."""
    from factory.core import config as config_module
    from factory.styles import STYLE_ENGINES

    cfg = config_module.charger(contexte.racine, strict=False)
    style = cfg.styles.get(contexte.spec.style)
    if style is None or style.engine not in STYLE_ENGINES:
        return None, f"style {contexte.spec.style} sans moteur livré"
    module = importlib.import_module(STYLE_ENGINES[style.engine].__module__)
    taille = getattr(module, "TAILLE_TITRE_PX", None)
    return taille, f"{module.__name__}.TAILLE_TITRE_PX"


def _taille_texte(contexte: ContexteQc) -> Mesure:
    """Plus petite taille de texte du rendu, en part de la hauteur de l'image."""
    seuil = contexte.seuil("text_legibility")
    minimum = float(seuil.get("min", 0.035))
    sous_titres = contexte.channel.charte.subtitles.size_px
    titre, origine_titre = _taille_moteur(contexte)
    tailles = {"sous-titres (charte)": sous_titres}
    if titre:
        tailles[f"texte à l'écran ({origine_titre})"] = titre
    plus_petite = min(tailles.values())
    part = plus_petite / HAUTEUR
    score = base.score_min(part, minimum, float(seuil.get("zero", 0.020)))
    detail = " · ".join(f"{nom} {px} px" for nom, px in tailles.items())
    return Mesure(
        nom="text_size", valeur=round(part, 4), unite="part de la hauteur", cible=minimum,
        source="paramètres de rendu (charte + moteur de style), pas d'OCR",
        origine_cible=f"{base.DECISION} — seuil de lisibilité sur vignette de téléphone",
        score=score, poids=1, statut=base.statut_depuis(score),
        note=f"{detail} — la plus petite fait {part:.1%} de {HAUTEUR} px",
    )


def _contraste(contexte: ContexteQc) -> Mesure:
    """Contraste WCAG médian, mesuré sur les bandeaux de texte de plusieurs plans."""
    seuil = contexte.seuil("text_contrast")
    minimum = float(seuil.get("min", 4.5))
    shotlist = contexte.shotlist
    params = contexte.mesure_param("lisibilite")
    if shotlist is None:
        return Mesure(
            nom="text_contrast", valeur=None, unite="ratio", cible=minimum,
            source="images extraites + Otsu + WCAG 2.1", origine_cible=base.REGISTRE,
            score=None, poids=2, statut="skipped", note="shotlist.json absent",
        )
    avec_texte = [s for s in shotlist.shots if (s.on_screen_text or "").strip()]
    if not avec_texte:
        return Mesure(
            nom="text_contrast", valeur=None, unite="ratio", cible=minimum,
            source="images extraites + Otsu + WCAG 2.1", origine_cible=base.REGISTRE,
            score=None, poids=2, statut="skipped", note="aucun plan à texte incrusté",
        )
    echantillon = int(params.get("plans_contraste", 5))
    pas = max(1, len(avec_texte) // echantillon)
    choisis = avec_texte[::pas][:echantillon]
    ratios = []
    for index, shot in enumerate(choisis):
        instant = min(
            shot.start_s + shot.duration_s / 2.0, max(0.0, contexte.duree_s - 0.05)
        )
        chemin = base.extraire_image(
            contexte.video, instant, contexte.dossier_travail / "texte" / f"{shot.id}.png"
        )
        ratio = _contraste_bandeau(chemin, params)
        if ratio is not None:
            ratios.append(ratio)
    if not ratios:
        # Objection C4, retenue : la shotlist annonce un texte et le bandeau n'en contient
        # aucun. Sauter la mesure ferait *gagner* la famille lisibilité — son poids quitterait
        # le dénominateur. C'est un défaut, pas une absence de cible : la note est 0.
        return Mesure(
            nom="text_contrast", valeur=0.0, unite="ratio", cible=minimum,
            source="images extraites + Otsu + WCAG 2.1",
            origine_cible=f"{base.REGISTRE} — miniatures.contraste_ratio_cible",
            score=0.0, poids=2, statut="fail",
            note=(
                f"{len(avec_texte)} plan(s) annoncent un texte incrusté et aucun bandeau n'en "
                "porte : soit le texte n'a pas été rendu, soit le moteur l'a déplacé hors du "
                "bandeau décrit dans config/qc.yaml → mesure.lisibilite"
            ),
        )
    median = statistics.median(ratios)
    score = base.score_min(median, minimum, float(seuil.get("zero", 1.5)))
    return Mesure(
        nom="text_contrast", valeur=round(median, 2), unite="ratio",
        cible=minimum, source="images extraites (ffmpeg) + Otsu + luminance WCAG 2.1",
        origine_cible=(
            f"{base.REGISTRE} — miniatures.contraste_ratio_cible 4,5 (WCAG AA), "
            "décision reprise du registre pour le texte à l'écran"
        ),
        score=score, poids=2, statut=base.statut_depuis(score),
        note=(
            f"{len(ratios)} bandeau(x) mesuré(s), du plus faible {min(ratios):.2f} "
            f"au plus fort {max(ratios):.2f}"
        ),
    )


def _contraste_bandeau(chemin, params: dict) -> float | None:
    """Contraste WCAG entre les deux classes d'Otsu du bandeau de texte d'une image."""
    import numpy as np
    from PIL import Image

    if not chemin.exists():
        return None
    haut = float(params.get("bandeau_haut", 0.72))
    bas = float(params.get("bandeau_bas", 0.97))
    gauche = float(params.get("bandeau_gauche", 0.12))
    droite = float(params.get("bandeau_droite", 0.88))
    with Image.open(chemin) as image:
        largeur, hauteur = image.size
        crop = image.convert("RGB").crop((
            int(gauche * largeur), int(haut * hauteur),
            int(droite * largeur), int(bas * hauteur),
        ))
    pixels = np.asarray(crop, dtype=np.float32)
    if pixels.size == 0:
        return None
    # Luminance relative WCAG, calculée en tableau : la boucle par pixel coûterait des minutes.
    lineaire = pixels / 255.0
    lineaire = np.where(
        lineaire <= 0.04045, lineaire / 12.92, ((lineaire + 0.055) / 1.055) ** 2.4
    )
    luminance = (
        0.2126 * lineaire[..., 0] + 0.7152 * lineaire[..., 1] + 0.0722 * lineaire[..., 2]
    )
    plat = luminance.ravel()
    seuil = _otsu(plat)
    clair, sombre = plat[plat > seuil], plat[plat <= seuil]
    part_minoritaire = min(clair.size, sombre.size) / plat.size
    if clair.size == 0 or sombre.size == 0:
        return None
    if part_minoritaire < float(params.get("part_texte_min", 0.005)):
        return None  # pas de texte dans le bandeau : rien à mesurer, pas un mauvais contraste
    # Le texte est la classe minoritaire ; le fond est pris au percentile le PLUS PROCHE du
    # texte, et non à sa moyenne. Un fond hétérogène — une image claire sous un cartouche
    # translucide — donnerait sinon un contraste flatteur là où le texte disparaît vraiment.
    texte, fond = (clair, sombre) if clair.size <= sombre.size else (sombre, clair)
    percentile = 90.0 if texte is clair else 10.0
    return base.contraste_wcag(
        float(texte.mean()), float(np.percentile(fond, percentile))
    )


def _otsu(valeurs) -> float:
    """Seuil d'Otsu sur un vecteur de luminances 0-1, par histogramme de 256 classes."""
    import numpy as np

    histogramme, bords = np.histogram(valeurs, bins=256, range=(0.0, 1.0))
    centres = (bords[:-1] + bords[1:]) / 2.0
    total = histogramme.sum()
    if total == 0:
        return 0.5
    poids_bas = np.cumsum(histogramme)
    poids_haut = total - poids_bas
    somme = np.cumsum(histogramme * centres)
    somme_totale = somme[-1]
    valides = (poids_bas > 0) & (poids_haut > 0)
    moyenne_bas = np.where(valides, somme / np.maximum(poids_bas, 1), 0.0)
    moyenne_haut = np.where(valides, (somme_totale - somme) / np.maximum(poids_haut, 1), 0.0)
    variance = poids_bas * poids_haut * (moyenne_bas - moyenne_haut) ** 2
    variance = np.where(valides, variance, -1.0)
    return float(centres[int(np.argmax(variance))])


def _mots_a_l_ecran(contexte: ContexteQc) -> Mesure:
    """Nombre médian de mots par texte incrusté, et part des textes trop longs."""
    seuil = contexte.seuil("on_screen_words")
    maximum = float(seuil.get("max", 6))
    shotlist = contexte.shotlist
    if shotlist is None:
        return Mesure(
            nom="on_screen_words", valeur=None, unite="mots", cible=maximum,
            source="shotlist.json", origine_cible=base.DECISION, score=None, poids=1,
            statut="skipped", note="shotlist.json absent",
        )
    longueurs = [
        len((s.on_screen_text or "").split()) for s in shotlist.shots
        if (s.on_screen_text or "").strip()
    ]
    if not longueurs:
        return Mesure(
            nom="on_screen_words", valeur=None, unite="mots", cible=maximum,
            source="shotlist.json", origine_cible=base.DECISION, score=None, poids=1,
            statut="skipped", note="aucun texte incrusté",
        )
    trop_longs = [n for n in longueurs if n > maximum]
    part = len(trop_longs) / len(longueurs)
    score = base.score_max(part, 0.0, float(seuil.get("zero_part", 0.30)))
    return Mesure(
        nom="on_screen_words", valeur=round(statistics.median(longueurs), 1), unite="mots",
        cible=maximum, source="shotlist.json — on_screen_text",
        origine_cible=f"{base.DECISION} — plafond de production, aucune mesure de registre",
        score=score, poids=1, statut=base.statut_depuis(score),
        note=(
            f"{len(trop_longs)}/{len(longueurs)} texte(s) au-delà de {maximum:g} mots "
            f"({part:.0%}) ; le plus long en fait {max(longueurs)}"
        ),
    )
