"""Helpers ffmpeg communs à tous les moteurs de style à backend `ffmpeg`.

Trois familles de fonctions, et rien d'autre :

1. **Polices** — résolution d'un nom de charte (« Inter SemiBold ») vers un fichier OFL de
   `assets/fonts/`, avec l'instance de graisse d'une police variable.
2. **Calques** — rastérisation d'un calque de texte ou de carte en PNG RGBA (Pillow), parce que
   **le ffmpeg de cette machine n'a pas `drawtext`** : la build Homebrew 8.1.2 est compilée sans
   `libfreetype`, `libfontconfig` ni `libass` (`No such filter: 'drawtext'`, mesuré le 16/09/2026).
   Le rendu vidéo reste entièrement ffmpeg ; seul le texte est gravé en amont, ce qui donne en
   prime le retour à la ligne mesuré au pixel, impossible avec `drawtext` qui n'en a aucun.
3. **Filtres et encodage** — fond uni, dégradé animé, `zoompan` suréchantillonné, apparition par
   alpha, encodage au contrat de `INTERFACES.md` (H.264 `yuv420p`, 1920×1080, 30 ips constantes,
   sans audio), et `verify_clip` qui mesure au lieu de croire.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Literal, Sequence

from PIL import Image, ImageDraw, ImageFont

from factory.core.paths import racine_projet

#: Contrat de format de `clips/shot_XX.mp4` (`INTERFACES.md` § clips).
LARGEUR, HAUTEUR = 1920, 1080
FPS = 30
#: Le contrat dit `-crf 18` ; le prompt de l'étape 12.1 disait 16. Le contrat gagne : c'est lui
#: que le QC relira, et 18 à 1080p est déjà visuellement transparent sur des aplats de charte.
CRF = 18
#: Tolérance de durée d'un clip : ± 1 image (`INTERFACES.md`), soit 1/30 s ≈ 0,033 s.
TOLERANCE_DUREE_S = 0.05

#: Dossier des polices OFL redistribuables (`outils/LICENCES.md`).
DOSSIER_POLICES = "assets/fonts"
#: Nom de fichier par famille. Une police variable porte ses graisses en instances nommées.
FICHIERS_POLICES: dict[str, str] = {"inter": "Inter[opsz,wght].ttf"}
#: Graisses reconnues dans un nom de charte, de la plus longue à la plus courte (« ExtraBold »
#: avant « Bold », sinon « Inter ExtraBold » se résoudrait en « Bold »).
GRAISSES: tuple[str, ...] = (
    "ExtraLight", "ExtraBold", "SemiBold", "Regular", "Medium",
    "Light", "Black", "Thin", "Bold",
)


class FfmpegError(RuntimeError):
    """Un appel ffmpeg ou ffprobe a échoué ; le message porte la sortie exacte de l'outil."""


# --------------------------------------------------------------------------------------
# Polices
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Police:
    """Une police de charte résolue en fichier sur disque."""

    nom_charte: str
    fichier: Path
    graisse: str

    def charger(self, taille_px: int) -> ImageFont.FreeTypeFont:
        """Instancie la police à une taille, graisse appliquée si la police est variable."""
        fonte = ImageFont.truetype(str(self.fichier), taille_px)
        try:
            disponibles = {n.decode("utf-8", "ignore") for n in fonte.get_variation_names()}
        except OSError:
            return fonte  # police statique : la graisse est dans le fichier
        if self.graisse in disponibles:
            fonte.set_variation_by_name(self.graisse)
        return fonte


def resoudre_police(nom_charte: str, racine: Path | None = None) -> Police:
    """« Inter SemiBold » → `assets/fonts/Inter[opsz,wght].ttf` + instance « SemiBold ».

    Lève `FileNotFoundError` en nommant le fichier attendu : une police absente doit arrêter le
    rendu, pas le laisser tomber en silence sur une police système non redistribuable.
    """
    base = racine or racine_projet()
    graisse = "Regular"
    reste = nom_charte.strip()
    for candidate in GRAISSES:
        if reste.lower().endswith(candidate.lower()):
            graisse = candidate
            reste = reste[: -len(candidate)].strip()
            break
    famille = reste.replace(" ", "").lower()
    if famille not in FICHIERS_POLICES:
        connues = ", ".join(sorted(FICHIERS_POLICES))
        raise FileNotFoundError(
            f"police « {nom_charte} » : famille {reste!r} inconnue (connues : {connues}) — "
            f"dépose le fichier OFL dans {DOSSIER_POLICES}/ et inscris-le dans outils/LICENCES.md"
        )
    fichier = base / DOSSIER_POLICES / FICHIERS_POLICES[famille]
    if not fichier.exists():
        raise FileNotFoundError(f"police « {nom_charte} » : fichier absent — {fichier}")
    return Police(nom_charte=nom_charte, fichier=fichier, graisse=graisse)


# --------------------------------------------------------------------------------------
# Calques rastérisés
# --------------------------------------------------------------------------------------


def _rvba(couleur: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    """« #101820 » → (16, 24, 32, 255)."""
    brut = couleur.lstrip("#")
    return (int(brut[0:2], 16), int(brut[2:4], 16), int(brut[4:6], 16), round(255 * alpha))


def decouper_lignes(texte: str, fonte: ImageFont.FreeTypeFont, largeur_max: int) -> list[str]:
    """Retour à la ligne aux espaces, mesuré au pixel sur la fonte réelle.

    Un mot plus large que la boîte reste seul sur sa ligne : on ne coupe pas un mot, la ligne
    déborderait moins mais serait illisible.
    """
    lignes: list[str] = []
    courante = ""
    for mot in texte.split():
        essai = f"{courante} {mot}".strip()
        if courante and fonte.getlength(essai) > largeur_max:
            lignes.append(courante)
            courante = mot
        else:
            courante = essai
    if courante:
        lignes.append(courante)
    return lignes


def ajuster_taille(
    texte: str, police: Police, largeur_max: int, taille_px: int, lignes_max: int
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    """Réduit la taille par pas de 4 px jusqu'à tenir en `lignes_max`, plancher à 40 % de la taille.

    Rend la fonte retenue et les lignes découpées. Au plancher, les lignes en trop sont coupées et
    la dernière reçoit une ellipse : mieux vaut un texte tronqué qu'un texte hors cadre.
    """
    plancher = max(24, round(taille_px * 0.4))
    taille = taille_px
    while taille >= plancher:
        fonte = police.charger(taille)
        lignes = decouper_lignes(texte, fonte, largeur_max)
        if len(lignes) <= lignes_max and all(fonte.getlength(l) <= largeur_max for l in lignes):
            return fonte, lignes
        taille -= 4
    fonte = police.charger(plancher)
    lignes = decouper_lignes(texte, fonte, largeur_max)
    if len(lignes) > lignes_max:
        lignes = lignes[: lignes_max - 1] + [lignes[lignes_max - 1].rstrip(" ,;:") + "…"]
    return fonte, lignes


def rasteriser_texte(
    texte: str,
    police: Police,
    taille_px: int,
    couleur: str,
    largeur_max: int,
    lignes_max: int = 3,
    contour: str | None = None,
    contour_px: int = 0,
    interligne: float = 1.18,
) -> Image.Image:
    """Rend un bloc de texte centré en PNG RGBA à la taille exacte de son encombrement."""
    fonte, lignes = ajuster_taille(texte, police, largeur_max, taille_px, lignes_max)
    hauteur_ligne = round(fonte.size * interligne)
    largeur = max(1, round(max(fonte.getlength(l) for l in lignes))) + 2 * contour_px
    hauteur = hauteur_ligne * len(lignes) + 2 * contour_px + round(fonte.size * 0.3)
    calque = Image.new("RGBA", (largeur, hauteur), (0, 0, 0, 0))
    dessin = ImageDraw.Draw(calque)
    for index, ligne in enumerate(lignes):
        x = largeur / 2
        y = contour_px + index * hauteur_ligne
        dessin.text(
            (x, y), ligne, font=fonte, fill=_rvba(couleur), anchor="ma",
            stroke_width=contour_px if contour else 0,
            stroke_fill=_rvba(contour) if contour else None,
        )
    return calque


def rectangle_arrondi(
    taille: tuple[int, int], rayon: int, remplissage: str, alpha: float = 1.0,
    bordure: str | None = None, bordure_px: int = 0,
) -> Image.Image:
    """Une carte : rectangle à coins arrondis en RGBA. `drawbox` de ffmpeg n'arrondit pas."""
    calque = Image.new("RGBA", taille, (0, 0, 0, 0))
    dessin = ImageDraw.Draw(calque)
    dessin.rounded_rectangle(
        [(0, 0), (taille[0] - 1, taille[1] - 1)], radius=rayon,
        fill=_rvba(remplissage, alpha),
        outline=_rvba(bordure) if bordure else None, width=bordure_px if bordure else 0,
    )
    return calque


def coller(fond: Image.Image, calque: Image.Image, position: tuple[int, int]) -> None:
    """Compose `calque` sur `fond` en respectant son alpha (Pillow ne le fait pas seul)."""
    fond.alpha_composite(calque, dest=position)


# --------------------------------------------------------------------------------------
# Fragments de filtre ffmpeg
# --------------------------------------------------------------------------------------


def source_couleur(couleur: str, duree_s: float, taille: tuple[int, int] | None = None) -> str:
    """Fond uni, en source `lavfi`."""
    largeur, hauteur = taille or (LARGEUR, HAUTEUR)
    return f"color=c={couleur}:s={largeur}x{hauteur}:r={FPS}:d={duree_s:.3f}"


def melanger(couleur_a: str, couleur_b: str, part_b: float) -> str:
    """Mélange deux couleurs de charte. Sert à teinter un fond sans employer l'accent pur."""
    a, b = _rvba(couleur_a)[:3], _rvba(couleur_b)[:3]
    melange = tuple(round(x + (y - x) * part_b) for x, y in zip(a, b))
    return "#{:02x}{:02x}{:02x}".format(*melange)


def source_degrade(
    couleurs: Sequence[str], duree_s: float, vitesse: float = 0.012,
    taille: tuple[int, int] | None = None, graine: int | None = None,
    diagonale: int = 0,
) -> str:
    """Dégradé animé lent, en source `lavfi` (`gradients`).

    **Deux couleurs et des extrémités imposées**, mesuré le 16/09/2026 : au-delà de deux couleurs,
    ou avec les `x0/y0/x1/y1` par défaut (aléatoires), `gradients` répète le motif et laisse une
    **bande à bord franc** en travers de l'image, qui dispute la lecture au texte. Les quatre
    diagonales donnent la variation d'un plan à l'autre ; `seed` fixe la rotation, sans quoi deux
    rendus du même plan diffèrent.

    `speed` très bas : le fond doit respirer, pas attirer l'œil.
    """
    largeur, hauteur = taille or (LARGEUR, HAUTEUR)
    palette = list(couleurs)[:2]
    couleurs_filtre = ":".join(f"c{i}={c}" for i, c in enumerate(palette))
    coins = [
        (0, 0, largeur, hauteur), (largeur, 0, 0, hauteur),
        (0, hauteur, largeur, 0), (largeur, hauteur, 0, 0),
    ][diagonale % 4]
    ancre = f":seed={graine % (2**32)}" if graine is not None else ""
    return (
        f"gradients=s={largeur}x{hauteur}:{couleurs_filtre}:nb_colors={len(palette)}"
        f":x0={coins[0]}:y0={coins[1]}:x1={coins[2]}:y1={coins[3]}"
        f":speed={vitesse:.4f}:r={FPS}:d={duree_s:.3f}:type=linear{ancre}"
    )


def filtre_zoompan(
    mouvement: str, duree_s: float, surechantillonnage: int = 1,
    taille: tuple[int, int] | None = None,
) -> str:
    """Ken Burns par `zoompan`, appliqué image par image (`d=1`) à un flux déjà animé.

    Le surechantillonnage ×4 de `ARCHITECTURE.md` § 5 supprime le jitter de `zoompan` sur une
    image fixe détaillée. Sur un dégradé il n'y a aucun détail à faire trembler : `cartes` appelle
    donc avec 1, et le paramètre reste là pour `illustre` (étape 12.2).
    """
    largeur, hauteur = taille or (LARGEUR, HAUTEUR)
    images = max(1, round(duree_s * FPS))
    if mouvement == "static":
        return ""
    amplitude = 0.10
    pas = amplitude / images
    avant = f"scale={largeur * surechantillonnage}:{hauteur * surechantillonnage}:flags=bicubic,"
    if mouvement == "zoom_in":
        zoom, x, y = f"min(zoom+{pas:.6f},{1 + amplitude:.3f})", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mouvement == "zoom_out":
        zoom = f"max({1 + amplitude:.3f}-on*{pas:.6f},1.0)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mouvement == "pan":
        zoom = f"{1 + amplitude:.3f}"
        x = f"(iw-iw/zoom)*on/{images}"
        y = "ih/2-(ih/zoom/2)"
    else:  # parallax : pas de carte de profondeur ici, le moteur ne doit pas le demander
        raise ValueError(f"mouvement {mouvement!r} : non rendu par le backend ffmpeg sans profondeur")
    return (
        f"{avant if surechantillonnage > 1 else ''}"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={largeur}x{hauteur}:fps={FPS}"
    )


def filtre_apparition(duree_s: float, delai_s: float = 0.0) -> str:
    """Apparition d'un calque par rampe d'alpha — jamais un `cut` sec sur du texte."""
    return f"fade=t=in:st={delai_s:.3f}:d={duree_s:.3f}:alpha=1"


# --------------------------------------------------------------------------------------
# Exécution et vérification
# --------------------------------------------------------------------------------------


def _binaire(nom: str) -> str:
    chemin = shutil.which(nom)
    if chemin is None:
        raise FfmpegError(f"{nom} introuvable dans le PATH")
    return chemin


def lancer_ffmpeg(arguments: list[str], journal: IO[str] | None = None) -> float:
    """Lance ffmpeg, renvoie le temps écoulé. Toute la sortie part au journal, jamais à l'écran."""
    import time

    commande = [_binaire("ffmpeg"), "-hide_banner", "-nostdin", "-y", *arguments]
    debut = time.perf_counter()
    resultat = subprocess.run(commande, capture_output=True, text=True, check=False)
    ecoule = time.perf_counter() - debut
    if journal is not None:
        journal.write(f"$ {' '.join(commande)}\n{resultat.stderr}\n")
        journal.flush()
    if resultat.returncode != 0:
        derniere = [l for l in resultat.stderr.strip().splitlines() if l.strip()][-6:]
        raise FfmpegError(f"ffmpeg code {resultat.returncode} :\n" + "\n".join(derniere))
    return ecoule


@dataclass(frozen=True)
class InfoClip:
    """Ce que `ffprobe` mesure d'un clip — jamais ce que le rendu a déclaré."""

    largeur: int
    hauteur: int
    fps: float
    duree_s: float
    images: int
    codec: str
    pix_fmt: str
    audio: bool


def ffprobe_clip(chemin: Path) -> InfoClip:
    """Mesure un clip. Lève `FfmpegError` si `ffprobe` échoue ou si le fichier n'a pas de vidéo."""
    commande = [
        _binaire("ffprobe"), "-v", "error", "-show_streams", "-show_format",
        "-of", "json", str(chemin),
    ]
    resultat = subprocess.run(commande, capture_output=True, text=True, check=False)
    if resultat.returncode != 0:
        raise FfmpegError(f"ffprobe {chemin.name} : {resultat.stderr.strip()}")
    charge = json.loads(resultat.stdout)
    flux_video = [f for f in charge.get("streams", []) if f.get("codec_type") == "video"]
    if not flux_video:
        raise FfmpegError(f"ffprobe {chemin.name} : aucun flux vidéo")
    flux = flux_video[0]
    numerateur, _, denominateur = flux.get("avg_frame_rate", "0/1").partition("/")
    fps = float(numerateur) / float(denominateur) if float(denominateur) else 0.0
    images = int(flux.get("nb_frames") or 0)
    duree = float(flux.get("duration") or charge.get("format", {}).get("duration") or 0.0)
    if images and fps:
        duree = images / fps  # la durée de conteneur arrondit ; le compte d'images ne ment pas
    return InfoClip(
        largeur=int(flux["width"]), hauteur=int(flux["height"]), fps=fps, duree_s=duree,
        images=images, codec=str(flux.get("codec_name", "")),
        pix_fmt=str(flux.get("pix_fmt", "")),
        audio=any(f.get("codec_type") == "audio" for f in charge.get("streams", [])),
    )


def verify_clip(
    chemin: Path, duree_attendue_s: float, tolerance_s: float = TOLERANCE_DUREE_S
) -> list[str]:
    """Rend la liste des écarts au contrat de format. Liste vide = clip conforme."""
    ecarts: list[str] = []
    if not chemin.exists():
        return [f"{chemin.name} : absent"]
    info = ffprobe_clip(chemin)
    if (info.largeur, info.hauteur) != (LARGEUR, HAUTEUR):
        ecarts.append(f"{chemin.name} : {info.largeur}×{info.hauteur} au lieu de {LARGEUR}×{HAUTEUR}")
    if abs(info.fps - FPS) > 0.01:
        ecarts.append(f"{chemin.name} : {info.fps:.3f} ips au lieu de {FPS}")
    if abs(info.duree_s - duree_attendue_s) > tolerance_s:
        ecarts.append(
            f"{chemin.name} : {info.duree_s:.3f} s au lieu de {duree_attendue_s:.3f} s "
            f"(écart {abs(info.duree_s - duree_attendue_s):.3f} s > {tolerance_s:.3f} s)"
        )
    if info.pix_fmt != "yuv420p":
        ecarts.append(f"{chemin.name} : pix_fmt {info.pix_fmt} au lieu de yuv420p")
    if info.audio:
        ecarts.append(f"{chemin.name} : piste audio présente, interdite sur un clip de plan")
    return ecarts


def arguments_encodage(sortie: Path, duree_s: float, crf: int = CRF) -> list[str]:
    """Queue d'arguments commune : H.264 `yuv420p`, 30 ips constantes, sans audio, durée exacte.

    La durée est imposée en **nombre d'images** (`-frames:v`) et non en `-t` : un `-t` laisse
    ffmpeg arrondir à l'échantillon près et le clip sort à ± 1 image de ce qu'il devait durer.
    """
    images = max(1, round(duree_s * FPS))
    return [
        "-frames:v", str(images), "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-pix_fmt", "yuv420p", "-r", str(FPS), "-fps_mode", "cfr",
        "-movflags", "+faststart", str(sortie),
    ]


Alignement = Literal["haut", "centre", "bas"]
