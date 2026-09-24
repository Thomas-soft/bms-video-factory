"""Socle du banc : ce qu'est une mesure, comment elle se note, et les sondes partagées.

Trois règles tiennent tout le module :

1. **Une mesure porte une unité, une cible et l'origine de cette cible.** `origine_cible` dit
   si la valeur vient du registre (`REFERENTIEL.json`), d'une décision de production
   (`config/qc.yaml`) ou d'un paramètre de rendu (la charte de la chaîne). Sans cela, l'étape 26
   corrélerait le score aux vues sans savoir ce qu'elle corrèle.
2. **Une cible marquée `a_mesurer` dans le référentiel n'est jamais notée comme un écart** :
   la mesure sort en `skipped`, son poids quitte le dénominateur (`INTERFACES.md` § qc.json).
3. **Le score partiel vaut 100 à la cible et décroît avec l'écart**, jusqu'à 0 au bord de la
   plage. Aucune fonction ne récompense le dépassement : passer sous la cible de rythme de coupe
   ne rapporte pas plus que l'atteindre — voir `score_cible`, qui est symétrique.

Aucun modèle n'est chargé ici : `ffmpeg`, `ffprobe`, PySceneDetect et Pillow, rien d'autre.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

Statut = Literal["pass", "warn", "fail", "skipped"]

#: Origines admises pour une cible. Écrites dans `qc.json`, lues par l'étape 26.
REGISTRE = "registre/REFERENTIEL.json"
DECISION = "config/qc.yaml"
CHARTE = "config/channels/<id>.yaml"


@dataclass
class Mesure:
    """Une mesure et sa note. `valeur is None` ⇒ `statut = skipped`, poids hors barème."""

    nom: str
    valeur: float | bool | None
    unite: str
    cible: float | str | None
    source: str
    origine_cible: str
    score: float | None = None
    poids: int = 1
    bloquant: bool = False
    statut: Statut = "pass"
    note: str = ""

    def json(self) -> dict[str, Any]:
        """Bloc `metrics[<nom>]` de `qc.json`."""
        return {
            "value": self.valeur,
            "unit": self.unite,
            "target": self.cible,
            "score": None if self.score is None else round(self.score, 1),
            "weight": self.poids,
            "blocking": self.bloquant,
            "status": self.statut,
            "source": self.source,
            "target_source": self.origine_cible,
            "note": self.note,
        }


@dataclass
class Famille:
    """Une famille de mesures et son poids au barème global."""

    nom: str
    poids: int
    mesures: list[Mesure] = field(default_factory=list)

    @property
    def notees(self) -> list[Mesure]:
        """Mesures qui comptent : celles dont la cible existait."""
        return [m for m in self.mesures if m.score is not None]

    @property
    def score(self) -> float | None:
        """Moyenne pondérée des mesures notées. `None` si la famille est entièrement `skipped`."""
        notees = self.notees
        if not notees:
            return None
        total = sum(m.poids for m in notees)
        return sum(m.score * m.poids for m in notees) / total if total else None


# --------------------------------------------------------------------------------------
# Fonctions de score partiel
# --------------------------------------------------------------------------------------

def score_cible(valeur: float, cible: float, tolerance: float, plage: float) -> float:
    """100 à ± `tolerance` de la cible (en part de la cible), 0 à ± `plage`, linéaire entre.

    Symétrique : un rythme deux fois trop rapide est puni autant qu'un rythme deux fois trop
    lent. C'est ce qui empêche le banc de récompenser les coupes inutiles.
    """
    if cible == 0:
        return 0.0
    ecart = abs(valeur - cible) / abs(cible)
    if ecart <= tolerance:
        return 100.0
    if ecart >= plage:
        return 0.0
    return 100.0 * (plage - ecart) / (plage - tolerance)


def score_min(valeur: float, minimum: float, zero: float) -> float:
    """100 au-dessus de `minimum`, 0 à `zero` (plus bas), linéaire entre. Pas de bonus au-delà."""
    if valeur >= minimum:
        return 100.0
    if valeur <= zero or minimum == zero:
        return 0.0
    return 100.0 * (valeur - zero) / (minimum - zero)


def score_max(valeur: float, maximum: float, zero: float) -> float:
    """100 sous `maximum`, 0 à `zero` (plus haut), linéaire entre."""
    if valeur <= maximum:
        return 100.0
    if valeur >= zero or zero == maximum:
        return 0.0
    return 100.0 * (zero - valeur) / (zero - maximum)


def score_intervalle(valeur: float, bas: float, haut: float, marge: float) -> float:
    """100 dans [`bas`, `haut`], 0 à `marge` au-delà de chaque borne."""
    if bas <= valeur <= haut:
        return 100.0
    if marge <= 0:
        return 0.0
    depassement = (bas - valeur) if valeur < bas else (valeur - haut)
    return max(0.0, 100.0 * (marge - depassement) / marge)


def score_booleen(ok: bool) -> float:
    """100 ou 0. Réservé à ce qui est vrai ou faux, jamais à ce qui se mesure."""
    return 100.0 if ok else 0.0


def statut_depuis(score: float, seuil_warn: float = 85.0, seuil_fail: float = 50.0) -> Statut:
    """`pass` / `warn` / `fail` à partir d'un score partiel."""
    if score >= seuil_warn:
        return "pass"
    return "warn" if score >= seuil_fail else "fail"


# --------------------------------------------------------------------------------------
# Sondes — ffprobe, ffmpeg, PySceneDetect
# --------------------------------------------------------------------------------------

def _binaire(nom: str) -> str:
    chemin = shutil.which(nom)
    if chemin is None:
        raise RuntimeError(f"{nom} introuvable dans le PATH")
    return chemin


def _ffmpeg(args: list[str]) -> str:
    """Lance ffmpeg et rend stderr (les filtres de mesure y écrivent)."""
    sortie = subprocess.run(
        [_binaire("ffmpeg"), "-hide_banner", "-nostats", *args],
        capture_output=True, text=True, check=False,
    )
    return sortie.stderr


def sonde(chemin: Path) -> dict[str, Any]:
    """`ffprobe` complet : flux et conteneur."""
    sortie = subprocess.run(
        [_binaire("ffprobe"), "-v", "error", "-show_streams", "-show_format", "-of", "json",
         str(chemin)],
        capture_output=True, text=True, check=False,
    )
    if sortie.returncode != 0:
        raise RuntimeError(f"ffprobe {chemin.name} : {sortie.stderr.strip()}")
    return json.loads(sortie.stdout)


def detecter_scenes(
    chemin: Path, seuil: float, min_scene_s: float, fps: float = 30.0
) -> list[tuple[float, float]]:
    """Plans détectés par PySceneDetect `ContentDetector`, en secondes.

    `ContentDetector` plutôt qu'`AdaptiveDetector` : le banc compare une **cadence** à une cible
    de niche, et un seuil fixe rend deux vidéos comparables entre elles. `AdaptiveDetector`
    normalise par une fenêtre glissante — utile contre les faux positifs d'une caméra qui bouge,
    inutile ici (nos plans sont des images fixes animées) et il déplacerait la cible d'une vidéo
    à l'autre. Le seuil vit dans `config/qc.yaml`, jamais dans le code.

    `min_scene_len` est en **images** dans l'API : la conversion depuis les secondes se fait ici,
    sinon un fondu de 0,32 s scinderait un plan en deux.
    """
    from scenedetect import ContentDetector, detect

    scenes = detect(
        str(chemin),
        ContentDetector(threshold=seuil, min_scene_len=max(1, round(min_scene_s * fps))),
        show_progress=False,
    )
    return [(debut.get_seconds(), fin.get_seconds()) for debut, fin in scenes]


_RE_SILENCE_DEBUT = re.compile(r"silence_start:\s*(-?[\d.]+)")
_RE_SILENCE_FIN = re.compile(r"silence_end:\s*(-?[\d.]+)\s*\|\s*silence_duration:\s*([\d.]+)")


def detecter_silences(
    chemin: Path, seuil_db: float, duree_min_s: float
) -> list[tuple[float, float]]:
    """Silences `(début, durée)` rendus par `silencedetect`.

    Le filtre n'imprime `silence_end` que lorsque le silence se referme : un silence qui court
    jusqu'à la fin du fichier n'a pas de fin imprimée et serait perdu. Il est rattrapé ici.
    """
    stderr = _ffmpeg([
        "-i", str(chemin), "-map", "0:a:0", "-vn",
        "-af", f"silencedetect=noise={seuil_db}dB:d={duree_min_s}", "-f", "null", "-",
    ])
    debuts = [float(v) for v in _RE_SILENCE_DEBUT.findall(stderr)]
    fins = [(float(f), float(d)) for f, d in _RE_SILENCE_FIN.findall(stderr)]
    silences = [(fin - duree, duree) for fin, duree in fins]
    if len(debuts) > len(fins):  # silence ouvert à la fin du fichier
        duree_totale = float(sonde(chemin)["format"]["duration"])
        silences.append((debuts[-1], max(0.0, duree_totale - debuts[-1])))
    return silences


_RE_MEAN = re.compile(r"mean_volume:\s*(-?[\d.]+) dB")


def volume_moyen(chemin: Path, debut_s: float, duree_s: float) -> float | None:
    """`mean_volume` d'une fenêtre, en dBFS. Sert à estimer le rapport musique/voix."""
    stderr = _ffmpeg([
        "-ss", f"{debut_s:.3f}", "-t", f"{duree_s:.3f}", "-i", str(chemin),
        "-map", "0:a:0", "-vn", "-af", "volumedetect", "-f", "null", "-",
    ])
    trouves = _RE_MEAN.findall(stderr)
    return float(trouves[-1]) if trouves else None


def extraire_image(chemin: Path, instant_s: float, sortie: Path, largeur: int = 0) -> Path:
    """Une image à `instant_s`. `-ss` **avant** `-i` : recherche par mots-clés, ~0,1 s.

    Placé après `-i`, ffmpeg décoderait depuis le début du fichier à chaque appel — 124 plans
    feraient passer le banc de quarante secondes à plusieurs heures.
    """
    sortie.parent.mkdir(parents=True, exist_ok=True)
    args = ["-ss", f"{instant_s:.3f}", "-i", str(chemin), "-frames:v", "1", "-update", "1"]
    if largeur:
        args += ["-vf", f"scale={largeur}:-2"]
    _ffmpeg([*args, "-y", str(sortie)])
    return sortie


# --------------------------------------------------------------------------------------
# Couleur — contraste WCAG
# --------------------------------------------------------------------------------------

def luminance_relative(r: float, v: float, b: float) -> float:
    """Luminance relative WCAG 2.1 d'un pixel sRGB donné en 0-255."""
    def canal(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * canal(r) + 0.7152 * canal(v) + 0.0722 * canal(b)


def contraste_wcag(l1: float, l2: float) -> float:
    """Rapport de contraste WCAG : (L_clair + 0,05) / (L_sombre + 0,05), de 1:1 à 21:1."""
    clair, sombre = max(l1, l2), min(l1, l2)
    return (clair + 0.05) / (sombre + 0.05)


_RE_YAVG = re.compile(r"lavfi\.signalstats\.YAVG=([\d.]+)")


def mouvement_moyen(chemin: Path, fenetre_s: float) -> float | None:
    """Mouvement moyen sur les `fenetre_s` premières secondes, en niveaux de luminance 0-255.

    `tblend=all_mode=difference` soustrait chaque image de la précédente, `signalstats` en donne
    la luminance moyenne : un plan strictement fixe rend 0, un Ken Burns lent environ 0,7, une
    coupe franche plusieurs unités. Mesuré à 1,1 s sur une vidéo de 12 minutes — dix fois moins
    cher que d'extraire et comparer des images en Python.
    """
    stderr = _ffmpeg([
        "-t", f"{fenetre_s:.3f}", "-i", str(chemin), "-an",
        "-vf", "tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG",
        "-f", "null", "-",
    ])
    valeurs = [float(v) for v in _RE_YAVG.findall(stderr)]
    return sum(valeurs) / len(valeurs) if valeurs else None
