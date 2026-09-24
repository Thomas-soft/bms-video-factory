#!/usr/bin/env python3
"""Dessine les deux mains du moteur « whiteboard » et les écrit dans `assets/charte/`.

Pourquoi les dessiner plutôt que les générer ou les télécharger : une main est un **asset de
charte**, elle apparaît sur tous les plans de tous les runs de ce style. Une main téléchargée
demanderait une licence à suivre et une attribution à porter ; une main générée par diffusion
demanderait un détourage, et FLUX dessine mal les mains (mesure de l'étape 5.2). Celle-ci est
tracée par du code, elle est donc à nous, reproductible et sans crédit à verser.

    uv run python outils/mains_whiteboard.py

Deux variantes : `main.png` tient un marqueur épais, `main_2.png` un feutre fin. Le **point de
tracé** — la pointe du feutre — est en haut à gauche de l'image, aux coordonnées `POINTE`, et
c'est ce point que la scène `draw-svg` cale sur l'extrémité du chemin en cours.
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

#: Taille de la planche. La main occupe ~1/4 de la hauteur d'une image 1080p au rendu.
TAILLE = (460, 560)
#: Pointe du feutre, en pixels de la planche. La scène pose ce point sur le trait.
POINTE = (44, 40)
#: Trait de contour, comme le reste du dessin au trait.
ENCRE = (26, 26, 26, 255)
PAPIER = (255, 255, 255, 255)
EPAISSEUR = 7


def _capsule(dessin: ImageDraw.ImageDraw, a: tuple[float, float], b: tuple[float, float],
             rayon: float, remplissage, contour) -> None:
    """Un doigt : un segment épais aux bouts ronds, contour compris."""
    dessin.line([a, b], fill=contour, width=int(rayon * 2 + EPAISSEUR), joint="curve")
    for centre in (a, b):
        r = rayon + EPAISSEUR / 2
        dessin.ellipse([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r], fill=contour)
    dessin.line([a, b], fill=remplissage, width=int(rayon * 2 - EPAISSEUR), joint="curve")
    for centre in (a, b):
        r = rayon - EPAISSEUR / 2
        dessin.ellipse([centre[0] - r, centre[1] - r, centre[0] + r, centre[1] + r],
                       fill=remplissage)


def _le_long(depart: tuple[float, float], angle_deg: float, distance: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return (depart[0] + math.cos(a) * distance, depart[1] + math.sin(a) * distance)


def dessiner_main(variante: int) -> Image.Image:
    """Une main qui tient un feutre, pointe en haut à gauche. `variante` 0 = marqueur, 1 = fin."""
    image = Image.new("RGBA", TAILLE, (0, 0, 0, 0))
    dessin = ImageDraw.Draw(image)

    # Le feutre file en diagonale depuis la pointe : c'est l'axe autour duquel tout se compose.
    angle = 47.0 if variante == 0 else 52.0
    demi_barre = 27.0 if variante == 0 else 19.0
    cone = 66.0 if variante == 0 else 54.0

    haut_barre = _le_long(POINTE, angle, cone)
    bas_barre = _le_long(POINTE, angle, 430.0)
    perp = angle + 90.0

    # Cône de la pointe, puis barre du corps : deux polygones qui se referment l'un sur l'autre.
    cone_polygone = [
        POINTE,
        _le_long(haut_barre, perp, demi_barre),
        _le_long(haut_barre, perp, -demi_barre),
    ]
    barre_polygone = [
        _le_long(haut_barre, perp, demi_barre),
        _le_long(bas_barre, perp, demi_barre),
        _le_long(bas_barre, perp, -demi_barre),
        _le_long(haut_barre, perp, -demi_barre),
    ]
    dessin.polygon(barre_polygone, fill=PAPIER, outline=ENCRE, width=EPAISSEUR)
    dessin.polygon(cone_polygone, fill=ENCRE if variante == 0 else PAPIER,
                   outline=ENCRE, width=EPAISSEUR)
    if variante == 1:
        # Feutre fin : seule la toute pointe est encrée.
        dessin.polygon(
            [POINTE, _le_long(_le_long(POINTE, angle, 22), perp, 9),
             _le_long(_le_long(POINTE, angle, 22), perp, -9)],
            fill=ENCRE,
        )

    # La paume est un galet posé sur l'axe du feutre, décalé du côté du pouce.
    centre_paume = _le_long(_le_long(POINTE, angle, 250.0), perp, -34.0)
    paume = [
        _le_long(centre_paume, angle - 96 + i * 30, 104 if i % 2 else 118) for i in range(12)
    ]
    dessin.polygon(paume, fill=PAPIER, outline=ENCRE, width=EPAISSEUR)

    # Quatre doigts repliés en travers de la barre, puis le pouce par-dessus : c'est cet ordre
    # qui fait lire la prise, et non un empilement de capsules.
    for index in range(4):
        base = _le_long(_le_long(POINTE, angle, 176.0 + index * 46.0), perp, -22.0)
        bout = _le_long(base, perp, 62.0 - index * 5.0)
        _capsule(dessin, base, bout, 25.0 - index * 1.6, PAPIER, ENCRE)
    pouce_base = _le_long(_le_long(POINTE, angle, 236.0), perp, -96.0)
    pouce_bout = _le_long(_le_long(POINTE, angle, 138.0), perp, -34.0)
    _capsule(dessin, pouce_base, pouce_bout, 29.0, PAPIER, ENCRE)

    # Poignet : il sort du cadre en bas à droite, sinon la main a l'air coupée net.
    poignet_a = _le_long(centre_paume, angle, 74.0)
    poignet_b = _le_long(POINTE, angle, 620.0)
    _capsule(dessin, poignet_a, poignet_b, 78.0, PAPIER, ENCRE)

    # Ombre portée très douce : elle décolle la main du papier sans la faire flotter.
    ombre = Image.new("RGBA", TAILLE, (0, 0, 0, 0))
    ImageDraw.Draw(ombre).polygon(paume, fill=(0, 0, 0, 52))
    ombre = ombre.filter(ImageFilter.GaussianBlur(16))
    planche = Image.new("RGBA", TAILLE, (0, 0, 0, 0))
    planche.alpha_composite(ombre, (10, 14))
    planche.alpha_composite(image)
    return planche.crop(planche.getbbox() or (0, 0, *TAILLE)) if False else planche


def main() -> None:
    racine = Path(__file__).resolve().parents[1]
    dossier = racine / "assets" / "charte"
    dossier.mkdir(parents=True, exist_ok=True)
    for variante, nom in enumerate(("main.png", "main_2.png")):
        chemin = dossier / nom
        dessiner_main(variante).save(chemin, "PNG", optimize=True)
        print(f"{chemin.relative_to(racine)} — {chemin.stat().st_size / 1024:.0f} Ko, "
              f"pointe {POINTE} sur {TAILLE[0]}×{TAILLE[1]}")


if __name__ == "__main__":
    main()
