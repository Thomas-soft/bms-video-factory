"""Mouvement d'une image fixe : parallaxe 2.5D, ou Ken Burns en repli.

**Le piège de la parallaxe, payé une fois à l'étape 5.2 et jamais deux.** Depth Anything rend une
profondeur **inverse** — clair = proche. Trois conséquences, toutes dans `_couches` :

1. Les rôles se lisent à l'endroit : la tranche **claire** est le premier plan, et c'est elle qui
   glisse le plus vite. Inversés, les plans partent à l'envers et l'œil le voit immédiatement.
2. Les masques sont **cumulatifs** : chaque couche porte tout ce qui est plus proche qu'elle, et
   le fond est l'image entière sans masque. Des masques mutuellement exclusifs laissent des trous
   dès que la couche glisse — on voit à travers, et le contrôle magenta les compte.
3. L'alpha suit une **rampe** autour du seuil, puis un flou gaussien : un seuil net crénèle les
   contours. C'est le « remplissage des trous » demandé par l'étape, et il coûte deux filtres
   Pillow, pas un modèle d'inpainting.

Les couches sont agrandies de 20 % pour que le glissement ne découvre jamais le bord : 192 px de
marge de chaque côté pour une dérive maximale de 130 px.

**Ken Burns est le repli, pas le parent pauvre** : noté 4/5 comme la parallaxe à l'étape 5.2, et
2,6 s par clip contre 3,7 s. Il sert quand la profondeur échoue, quand le plan est trop court
pour qu'un déplacement de couches se lise, et par décision de configuration.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import IO

from factory import video
from factory.assets import images
from factory.core.paths import racine_projet

#: Poids par défaut — surchargés par `config/styles/<id>.yaml` → `params.depth.model`.
MODELE_DEFAUT = "depth-anything/Depth-Anything-V2-Small-hf"
#: Seuils de profondeur des trois couches. Le premier est 0 : le fond est l'image entière.
SEUILS = (0.0, 0.34, 0.67)
#: Largeur de la rampe de fondu, en unités de profondeur, et rayon du flou de bord, en pixels.
BANDE = 0.06
FLOU = 3
#: Rayon du flou qui efface le sujet de la couche qui le porte en double. Assez large pour
#: qu'aucune silhouette ne reste lisible, assez court pour que la matière reste celle de
#: l'image — un aplat uni se verrait autant qu'un fantôme.
FLOU_FOND = 36
#: Agrandissement des couches, en part de l'image. Il n'existe que pour couvrir la dérive : au
#: delà, il agrandit une source 1280×720 vers 1080p et **coûte de la définition**. 0,06 laisse
#: 57 px de marge de chaque côté pour une dérive maximale de 30.
MARGE = 0.06
#: Dérive totale d'une couche sur la durée du plan, en pixels, à amplitude 1,0.
#:
#: **Mesuré le 16/09/2026, et c'est ce qui les a fait tomber de (10, 50, 130) à (3, 12, 30).**
#: La parallaxe 2.5D suppose une profondeur continue — un paysage, un intérieur. La charte
#: « illustre » produit l'inverse : un sujet net, isolé, sur un fond uni. Depth Anything y sépare
#: proprement l'objet du fond, mais faire glisser cet objet de 130 px **découvre 130 px de fond
#: qui n'existent pas** : on voit le sujet en double, puis une traînée floue une fois le fond
#: rempli. À 30 px, la découverte fait 1,6 % de la largeur : le mouvement se lit, le trou non.
DERIVES = (3.0, 12.0, 30.0)
#: En deçà de cette durée, un déplacement de couches ne se lit pas : Ken Burns.
DUREE_MINIMALE_PARALLAXE_S = 2.0
#: Amplitude du déplacement selon le mouvement demandé par le plan. Aucun plan n'est **figé** :
#: le mouvement continu est ce qui soutient l'attention (thèse n° 3).
AMPLITUDES = {"parallax": 1.0, "pan": 1.0, "zoom_in": 0.7, "zoom_out": 0.7, "static": 0.45}


class ProfondeurIndisponible(RuntimeError):
    """Le sous-processus de profondeur n'a rendu aucune carte exploitable."""


# --------------------------------------------------------------------------------------
# Profondeur — un sous-processus par run, pas par plan
# --------------------------------------------------------------------------------------

@dataclass
class ResultatProfondeur:
    """Ce que le lot de profondeur a produit."""

    cartes: dict[str, Path] = field(default_factory=dict)
    echecs: dict[str, str] = field(default_factory=dict)
    secondes: float = 0.0
    chargement_s: float = 0.0


def cartes_profondeur(
    demandes: list[tuple[Path, Path]], racine: Path | None = None,
    modele: str = MODELE_DEFAUT, journal: IO[str] | None = None,
) -> ResultatProfondeur:
    """Carte de profondeur de chaque image, en **un seul** sous-processus qui se termine.

    `demandes` associe chaque image à la destination de sa carte : c'est l'appelant qui nomme,
    parce que lui seul sait sous quelle identité l'image sera retrouvée au rendu. Les images déjà
    pourvues d'une carte ne sont pas repassées — la profondeur d'une image de bibliothèque est
    aussi réutilisable que l'image elle-même.
    """
    base = racine or racine_projet()
    resultat = ResultatProfondeur()
    paires: list[tuple[str, str]] = []
    for image, destination in demandes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.stat().st_size > 0:
            resultat.cartes[str(image)] = destination
            continue
        paires.append((str(image), str(destination)))

    if not paires:
        return resultat

    ou_va = {source: Path(cible) for source, cible in paires}

    commande = [
        sys.executable, "-m", "factory.assets._depth_worker",
        json.dumps({"paires": paires, "modele": modele}, ensure_ascii=False),
    ]
    depart = time.perf_counter()
    processus = subprocess.run(
        commande, capture_output=True, text=True, cwd=base, env=images.environnement(base)
    )
    resultat.secondes = time.perf_counter() - depart

    for ligne in (processus.stdout or "").splitlines():
        try:
            trace = json.loads(ligne)
        except json.JSONDecodeError:
            continue
        resultat.chargement_s = max(resultat.chargement_s, trace.get("chargement_s", 0.0))
        if trace.get("ok"):
            resultat.cartes[trace["source"]] = ou_va[trace["source"]]
        else:
            resultat.echecs[trace["source"]] = trace.get("erreur", "inconnue")

    if journal is not None:
        journal.write(
            f"profondeur : {len(resultat.cartes)} carte(s), {len(resultat.echecs)} échec(s) en "
            f"{resultat.secondes:.1f} s (chargement {resultat.chargement_s:.1f} s)\n"
        )
        if processus.returncode != 0:
            journal.write(f"profondeur : code {processus.returncode} — "
                          f"{(processus.stderr or '').strip()[-400:]}\n")
        journal.flush()

    if not resultat.cartes and paires:
        resultat.echecs.setdefault(
            "*", (processus.stderr or "").strip()[-400:] or "aucune carte produite"
        )
    return resultat


# --------------------------------------------------------------------------------------
# Découpe en couches
# --------------------------------------------------------------------------------------

def couches(
    image: Path, profondeur: Path, dossier: Path,
    taille: tuple[int, int] | None = None, nombre: int = 3,
) -> list[Path]:
    """Trois PNG RGBA cumulatifs, du fond au premier plan. Rend leurs chemins dans cet ordre."""
    import numpy as np
    from PIL import Image, ImageFilter

    largeur, hauteur = taille or (video.LARGEUR, video.HAUTEUR)
    dossier.mkdir(parents=True, exist_ok=True)
    existantes = [dossier / f"{image.stem}_L{i}.png" for i in range(nombre)]
    if all(p.exists() and p.stat().st_size > 0 for p in existantes):
        return existantes

    source = Image.open(image).convert("RGBA").resize((largeur, hauteur), Image.LANCZOS)
    carte = np.asarray(
        Image.open(profondeur).convert("L").resize((largeur, hauteur), Image.BILINEAR), dtype=float
    )
    carte = (carte - carte.min()) / max(carte.max() - carte.min(), 1e-6)

    seuils = list(SEUILS[:nombre] if nombre <= len(SEUILS) else SEUILS)
    # Les alphas d'abord, tous : chaque couche a besoin de celui de la couche qui la recouvre.
    alphas: list[Image.Image] = []
    for rang, seuil in enumerate(seuils):
        if rang == 0:
            plein = np.full(carte.shape, 255, dtype=np.uint8)   # le fond est plein : aucun trou
            alphas.append(Image.fromarray(plein, mode="L"))
        else:
            rampe = np.clip((carte - (seuil - BANDE / 2)) / BANDE, 0.0, 1.0)
            alphas.append(
                Image.fromarray((rampe * 255).astype(np.uint8), mode="L")
                .filter(ImageFilter.GaussianBlur(FLOU))
            )

    produites: list[Path] = []
    for rang in range(len(seuils)):
        # **Le remplissage des trous, et pourquoi il ne se voit qu'en mouvement.** Une couche
        # porte tout ce qui est plus proche qu'elle : le fond contient donc une copie **nette** du
        # sujet. Dès que la couche de devant glisse, cette copie reste en place et l'on voit le
        # sujet en double, puis en triple. Mesuré le 16/09/2026 sur le premier clip de cette
        # étape : trois losanges décalés au lieu d'un.
        # La parade est l'inpainting le moins cher qui soit — la zone recouverte par la couche
        # suivante est **floutée** dans celle-ci. Ce qui se découvre au glissement est alors un
        # fond plausible, jamais une silhouette.
        base = source
        if rang + 1 < len(seuils):
            base = Image.composite(
                source.filter(ImageFilter.GaussianBlur(FLOU_FOND)), source, alphas[rang + 1]
            )
        couche = base.copy()
        couche.putalpha(alphas[rang])
        destination = dossier / f"{image.stem}_L{rang}.png"
        couche.save(destination, "PNG")
        produites.append(destination)
    return produites


# --------------------------------------------------------------------------------------
# Clips
# --------------------------------------------------------------------------------------

def _sens(graine: int) -> int:
    """Sens du glissement, tiré de la graine du plan : deux plans voisins ne glissent pas pareil."""
    return 1 if graine % 2 == 0 else -1


def chaine_parallaxe(
    couches_png: list[Path], duree_s: float, mouvement: str, graine: int,
    amplitude_config: float = 1.0, apres: str = "format=yuv420p", etiquette: str = "v",
) -> str:
    """Filtre ffmpeg d'un plan en parallaxe : trois `overlay` à vitesses différenciées.

    La dérive est exprimée **en pixels sur la durée du plan**, jamais en pixels par seconde : un
    plan de 12 s et un plan de 3 s doivent parcourir la même distance, sinon le long dérive quatre
    fois plus et sort du cadre malgré la marge.
    """
    largeur = round(video.LARGEUR * (1 + MARGE))
    hauteur = round(video.HAUTEUR * (1 + MARGE))
    decalage_x = (largeur - video.LARGEUR) // 2
    decalage_y = (hauteur - video.HAUTEUR) // 2
    amplitude = AMPLITUDES.get(mouvement, 0.6) * amplitude_config
    sens = _sens(graine)
    duree = max(duree_s, 0.1)

    etiquettes = ["bg", "mid", "fg"][: len(couches_png)]
    parties = [
        f"[{i + 1}:v]scale={largeur}:{hauteur},setsar=1[{nom}];"
        for i, nom in enumerate(etiquettes)
    ]
    precedent = "[0:v]"
    for i, nom in enumerate(etiquettes):
        vitesse = DERIVES[i] * amplitude * sens / duree
        suivante = f"[o{i}]"
        parties.append(
            f"{precedent}[{nom}]overlay=x='-{decalage_x}+{vitesse:.4f}*t':y=-{decalage_y}{suivante};"
        )
        precedent = suivante
    queue = f"fps={video.FPS}" + (f",{apres}" if apres else "")
    parties.append(f"{precedent}{queue}[{etiquette}]")
    return "".join(parties)


def clip_parallaxe(
    couches_png: list[Path], duree_s: float, mouvement: str, graine: int, sortie: Path,
    journal: IO[str] | None = None, amplitude_config: float = 1.0,
) -> float:
    """Rend un clip de parallaxe 1080p30 de la durée exacte du plan. Retourne les secondes."""
    filtre = chaine_parallaxe(couches_png, duree_s, mouvement, graine, amplitude_config)
    arguments = [
        "-f", "lavfi",
        "-i", f"color=c=black:s={video.LARGEUR}x{video.HAUTEUR}:r={video.FPS}:d={duree_s:.3f}",
    ]
    for couche in couches_png:
        arguments += ["-loop", "1", "-t", f"{duree_s:.3f}", "-i", str(couche)]
    arguments += ["-filter_complex", filtre, "-map", "[v]"]
    arguments += video.arguments_encodage(sortie, duree_s)
    return video.lancer_ffmpeg(arguments, journal)


def clip_ken_burns(
    image: Path, duree_s: float, mouvement: str, graine: int, sortie: Path,
    journal: IO[str] | None = None, surechantillonnage: int = 4,
) -> float:
    """Repli Ken Burns : `zoompan` sur une image suréchantillonnée ×4, plus un pan léger.

    Deux pièges mesurés à l'étape 5.2, tous deux payés par ce filtre. Sans suréchantillonnage, le
    zoom saute d'un pixel sur une image détaillée. Et avec `-loop 1 -t` en entrée, `zoompan`
    produit `d` images **par image d'entrée** : l'entrée reste une image unique, la durée est
    imposée par `-frames:v`.
    """
    images = max(1, round(duree_s * video.FPS))
    grande_l = video.LARGEUR * surechantillonnage
    grande_h = video.HAUTEUR * surechantillonnage
    depart, arrivee = 1.0, 1.08
    if mouvement == "zoom_out" or (mouvement == "static" and _sens(graine) < 0):
        depart, arrivee = arrivee, depart
    pas = abs(arrivee - depart) / images
    if arrivee > depart:
        zoom = f"min(zoom+{pas:.6f},{arrivee:.3f})"
    else:
        zoom = f"max({depart:.3f}-on*{pas:.6f},{arrivee:.3f})"
    # Pan léger, borné à 3 % de la largeur : au-delà, il dispute la lecture au texte à l'écran.
    course = 0.03 * video.LARGEUR * _sens(graine)
    if mouvement == "pan":
        course *= 2
    x = f"iw/2-(iw/zoom/2)+{course:.1f}*on/{images}"
    y = "ih/2-(ih/zoom/2)"
    filtre = (
        f"scale={grande_l}:{grande_h}:flags=bicubic,"
        f"zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={video.LARGEUR}x{video.HAUTEUR}:fps={video.FPS},"
        f"format=yuv420p"
    )
    # Sans `-loop 1`, une image fixe ne fournit qu'une image et le clip sort à 0,033 s (16/09/2026).
    arguments = [
        "-loop", "1", "-framerate", str(video.FPS), "-t", f"{duree_s:.3f}", "-i", str(image),
        "-vf", filtre,
    ]
    arguments += video.arguments_encodage(sortie, duree_s)
    return video.lancer_ffmpeg(arguments, journal)


def trous_magenta(
    couches_png: list[Path], duree_s: float, mouvement: str, graine: int, temoin: Path,
    amplitude_config: float = 1.0,
) -> int:
    """Contrôle de non-régression : la dernière image sur fond magenta, tout pixel magenta = trou.

    C'est le contrôle qui a attrapé les masques exclusifs à l'étape 5.2. Il rejoue la composition
    en PNG (sans compression) sur un fond magenta et compte ce qui transparaît.
    """
    import numpy as np
    from PIL import Image

    filtre = chaine_parallaxe(couches_png, duree_s, mouvement, graine, amplitude_config)
    arguments = [
        "-f", "lavfi",
        "-i", f"color=c=magenta:s={video.LARGEUR}x{video.HAUTEUR}:r={video.FPS}:d={duree_s:.3f}",
    ]
    for couche in couches_png:
        arguments += ["-loop", "1", "-t", f"{duree_s:.3f}", "-i", str(couche)]
    arguments += [
        "-filter_complex", filtre, "-map", "[v]",
        "-ss", f"{max(duree_s - 0.1, 0.0):.3f}", "-frames:v", "1", str(temoin),
    ]
    video.lancer_ffmpeg(arguments, None)
    if not temoin.exists():
        return -1
    pixels = np.asarray(Image.open(temoin).convert("RGB"))
    compte = int(
        ((pixels[..., 0] > 240) & (pixels[..., 1] < 15) & (pixels[..., 2] > 240)).sum()
    )
    temoin.unlink()
    return compte
