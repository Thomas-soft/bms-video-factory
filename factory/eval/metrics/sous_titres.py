"""Famille « sous-titres » — couverture de la parole et longueur des lignes.

La couverture se mesure seconde à seconde : part des secondes où un mot est prononcé
(`words.json`) qui est couverte par un événement de sous-titre. Comparer des nombres de mots
donnerait une couverture flatteuse dès qu'un sous-titre déborde sur un silence.

L'absence de sous-titres est **bloquante** : c'est le seul défaut du banc dont on sache qu'il
coûte de l'audience sur toutes les niches, et il est gratuit à corriger.
"""

from __future__ import annotations

import re
from pathlib import Path

from factory.eval import base
from factory.eval.base import Famille, Mesure
from factory.eval.contexte import ContexteQc

_HORLOGE_SRT = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)
# Format ASS : Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text.
# Les six champs entre `End` et `Text` doivent être sautés, sans quoi « BMS,,0,0,0,, » est
# compté comme du texte et toutes les lignes paraissent 12 caractères trop longues.
_DIALOGUE_ASS = re.compile(
    r"^Dialogue:\s*[^,]*,(\d+:\d{2}:\d{2}\.\d{2}),(\d+:\d{2}:\d{2}\.\d{2}),"
    r"(?:[^,]*,){6}(.*)$",
    re.MULTILINE,
)
_BALISES_ASS = re.compile(r"\{[^}]*\}")


def mesurer(contexte: ContexteQc) -> Famille:
    """Couverture des secondes parlées et respect de la longueur de ligne."""
    famille = Famille("sous_titres", poids=contexte.qc.poids.get("sous_titres", 5))
    famille.mesures.append(_piste_livree(contexte))
    evenements, lignes, fichier = _lire(contexte)
    seuil_c = contexte.seuil("subtitle_coverage")
    cible = float(contexte.production.get("couverture_sous_titres", {}).get("cible", 1.0))
    minimum = float(seuil_c.get("min", 0.90))

    if not evenements:
        famille.mesures.append(Mesure(
            nom="subtitle_coverage", valeur=0.0, unite="part des secondes parlées", cible=cible,
            source="subtitles.srt / subtitles.ass", origine_cible=base.REGISTRE,
            score=0.0, poids=2, bloquant=True, statut="fail",
            note="aucun sous-titre : bloquant (prompt de l'étape 15)",
        ))
        return famille

    donnees = contexte.words
    if not donnees or not donnees.get("words"):
        famille.mesures.append(Mesure(
            nom="subtitle_coverage", valeur=None, unite="part des secondes parlées", cible=cible,
            source=f"{fichier} + words.json", origine_cible=base.REGISTRE, score=None,
            poids=2, statut="skipped", note="words.json absent : couverture non mesurable",
        ))
    else:
        couverture = _couverture(donnees["words"], evenements)
        score = base.score_min(couverture, minimum, float(seuil_c.get("zero", 0.50)))
        famille.mesures.append(Mesure(
            nom="subtitle_coverage", valeur=round(couverture, 4),
            unite="part des secondes parlées", cible=minimum,
            source=f"{fichier} croisé à words.json, pas de 0,1 s",
            origine_cible=(
                f"{base.REGISTRE} — production.couverture_sous_titres 1,0 ; plancher "
                f"{minimum:.0%} décidé dans {base.DECISION}"
            ),
            score=score, poids=1, bloquant=True,
            statut="fail" if couverture < minimum else base.statut_depuis(score),
            note=(
                f"{len(evenements)} événement(s). **Partiellement acquis par construction** "
                "(objection C1) : les sous-titres sont écrits depuis words.json, que cette "
                "mesure relit. Elle détecte l'absence, la troncature et la désynchronisation, "
                "pas la qualité du sous-titrage. Poids réduit à 1 pour cette raison"
            ),
        ))

    seuil_l = contexte.seuil("subtitle_line_length")
    maximum = int(seuil_l.get("max", 42))
    trop_longues = [ligne for ligne in lignes if len(ligne) > maximum]
    part = len(trop_longues) / len(lignes) if lignes else 0.0
    score_l = base.score_max(part, 0.0, float(seuil_l.get("zero_part", 0.10)))
    famille.mesures.append(Mesure(
        nom="subtitle_line_length", valeur=len(trop_longues), unite="lignes", cible=0,
        source=f"{fichier} — longueur en caractères",
        origine_cible=(
            f"{base.DECISION} — {maximum} caractères, plafond de lisibilité ; la charte "
            f"impose déjà {contexte.channel.charte.subtitles.max_chars_per_line}"
        ),
        score=score_l, poids=1, statut=base.statut_depuis(score_l),
        note=(
            f"{len(lignes)} ligne(s) au total"
            + (f" ; la plus longue fait {max(len(l) for l in lignes)} caractères" if lignes else "")
        ),
    ))
    return famille


def _lire(contexte: ContexteQc) -> tuple[list[tuple[float, float]], list[str], str]:
    """Événements `(début, fin)` et lignes de texte, depuis le .ass ou, à défaut, le .srt."""
    ass, srt = contexte.chemins.subtitles_ass, contexte.chemins.subtitles_srt
    if ass.exists():
        return (*_lire_ass(ass), ass.name)
    if srt.exists():
        return (*_lire_srt(srt), srt.name)
    return [], [], "aucun fichier"


def _lire_ass(chemin: Path) -> tuple[list[tuple[float, float]], list[str]]:
    evenements, lignes = [], []
    for debut, fin, texte in _DIALOGUE_ASS.findall(chemin.read_text(encoding="utf-8")):
        evenements.append((_horloge_ass(debut), _horloge_ass(fin)))
        propre = _BALISES_ASS.sub("", texte).replace("\\N", "\n")
        lignes += [l.strip() for l in propre.split("\n") if l.strip()]
    return evenements, lignes


def _horloge_ass(valeur: str) -> float:
    heures, minutes, secondes = valeur.split(":")
    return int(heures) * 3600 + int(minutes) * 60 + float(secondes)


def _lire_srt(chemin: Path) -> tuple[list[tuple[float, float]], list[str]]:
    contenu = chemin.read_text(encoding="utf-8")
    evenements = [
        (
            int(h1) * 3600 + int(m1) * 60 + int(s1) + int(ms1) / 1000,
            int(h2) * 3600 + int(m2) * 60 + int(s2) + int(ms2) / 1000,
        )
        for h1, m1, s1, ms1, h2, m2, s2, ms2 in _HORLOGE_SRT.findall(contenu)
    ]
    lignes = [
        ligne.strip() for ligne in contenu.splitlines()
        if ligne.strip() and not ligne.strip().isdigit() and "-->" not in ligne
    ]
    return evenements, lignes


def _couverture(mots: list[dict], evenements: list[tuple[float, float]], pas: float = 0.1) -> float:
    """Part des instants parlés couverts par un sous-titre, échantillonnés tous les `pas`."""
    parles = set()
    for mot in mots:
        debut, fin = float(mot["start_s"]), float(mot["end_s"])
        if fin <= debut:
            fin = debut + pas
        for index in range(int(debut / pas), int(fin / pas) + 1):
            parles.add(index)
    if not parles:
        return 0.0
    couverts = set()
    for debut, fin in evenements:
        for index in range(int(debut / pas), int(fin / pas) + 1):
            couverts.add(index)
    return len(parles & couverts) / len(parles)


def _piste_livree(contexte: ContexteQc) -> Mesure:
    """La piste de sous-titres est-elle dans le fichier livré ?

    Objection C1 du contradicteur, retenue : la couverture est acquise par construction, les
    sous-titres étant écrits depuis `words.json`. Ce contrôle-ci ne l'est pas — il interroge
    `final.mp4` par `ffprobe`, et attrape la seule panne réellement arrivée dans ce projet :
    des sous-titres produits et absents du conteneur. Une charte en `burn_in` n'a pas de piste
    séparée : le contrôle est alors tenu par construction, et le dit.
    """
    charte = contexte.channel.charte.subtitles
    pistes = [f for f in contexte.sonde["streams"] if f["codec_type"] == "subtitle"]
    if charte.burn_in:
        return Mesure(
            nom="subtitle_track", valeur=True, unite="booléen", cible=True,
            source="charte.subtitles.burn_in", origine_cible=base.CHARTE,
            score=100.0, poids=1, bloquant=True, statut="pass",
            note="sous-titres incrustés à l'image : aucune piste séparée attendue",
        )
    langues = [p.get("tags", {}).get("language", "?") for p in pistes]
    attendue = contexte.spec.lang
    correcte = bool(pistes) and any(l.startswith(attendue[:2]) for l in langues)
    return Mesure(
        nom="subtitle_track", valeur=correcte, unite="booléen", cible=True,
        source="ffprobe — flux de type subtitle du fichier livré",
        origine_cible=f"{base.DECISION} — bloquant : « sous-titres absents » (étape 15)",
        score=base.score_booleen(correcte), poids=1, bloquant=True,
        statut="pass" if correcte else "fail",
        note=(
            f"{len(pistes)} piste(s) {langues} pour la langue {attendue}"
            if pistes else "aucune piste de sous-titres dans final.mp4"
        ),
    )
