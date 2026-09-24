"""Trois miniatures composées, mesurées sur leurs pixels, et un plan de rotation.

**Pourquoi trois, et pourquoi une rotation.** YouTube a bien un test A/B de miniatures
(« Test & Compare », trois variantes, gagnant départagé sur la part de temps de visionnage,
test clos en deux semaines) mais il vit dans Studio **bureau** et n'a **aucune ressource dans
la Data API v3** : ni création, ni lecture, ni résultat. Vérifié à l'étape 21. La seule
comparaison qu'un système autonome puisse faire est donc une **rotation mesurée** : publier
la première, lire le CTR dans la Reporting API — la seule à donner les impressions — et poser
la suivante par `thumbnails.set` si le CTR décroche. Ce n'est pas une expérience contrôlée :
une rotation compare deux périodes, pas deux populations tirées au sort. Le manifeste dit
laquelle des deux il porte.

**Ce que « noté objectivement » veut dire ici.** Cinq mesures, toutes lues sur le PNG rendu,
aucune sur le HTML — une règle CSS dit ce qu'on a demandé, un pixel dit ce qu'on a obtenu.

- *Contraste* : rapport WCAG 2.x entre la couleur du texte et **les pixels réellement situés
  derrière lui**, obtenus en rendant la même page sans texte. Seuil 4,5:1.
- *Surface de texte* : part de l'image occupée par le bloc, en pourcentage.
- *Lisibilité à 168 × 94 px* — la taille d'une vignette dans le fil mobile. Deux choses s'y
  mesurent : la hauteur d'une ligne une fois réduite (≥ 10 px, la règle de production étant
  10 à 15 % de la hauteur en 1280×720, soit 9 à 14 px à 168) et la **netteté des contours**
  par variance du laplacien, qui chute quand un texte fin disparaît dans le rééchantillonnage.
- *Saillance sous le texte* : résidu spectral (Hou & Zhang), calculé en numpy. Il dit si le
  texte est posé **sur** le sujet de l'image — ce qui masque les deux à la fois — ou dans une
  zone calme. Aucune dépendance neuve : `cv2.saliency` vit dans `opencv-contrib`, qui n'est
  pas installé et ne le sera pas pour une carte de saillance de vingt lignes.
- *Distance de palette* : écart L*a*b* (CIE76) entre la couleur du texte et les couleurs
  dominantes du fond. Le contraste mesure la luminance seule ; deux couleurs de même clarté
  et de teintes opposées passent le contraste et restent illisibles.

**Les trois variantes doivent différer.** Elles partagent le fond du run (générer une image
de plus coûterait ~99 s pour une image que personne n'a validée) : si elles ne différaient
que par le texte, leurs mesures de composition seraient identiques et le score constaterait
l'ordre d'arrivée. Chacune combine donc un **texte**, un **gabarit** de la charte et une
**variante de palette** — trois combinaisons deux à deux distinctes, par construction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from factory.core.models import Charte, MesuresMiniature, VarianteMiniature

LARGEUR, HAUTEUR = 1280, 720
#: Taille d'affichage d'une vignette dans le fil mobile — là où la lisibilité se perd.
LARGEUR_VIGNETTE, HAUTEUR_VIGNETTE = 168, 94
#: Hauteur minimale d'une ligne de texte **dans la vignette**, en pixels.
HAUTEUR_TEXTE_MIN_PX = 10.0
#: Seuil WCAG AA pour du texte ordinaire. Un texte de miniature est du gros texte (seuil 3:1)
#: mais on retient le seuil strict : la vignette le ramène à une taille ordinaire.
CONTRASTE_MIN = 4.5
#: Limite YouTube pour un fichier de miniature.
POIDS_MAX_MO = 2.0
#: Variantes composées. Le contrat en exige 3 ; au-delà, on paie des rendus pour rien.
N_VARIANTES = 3
#: Marge latérale laissée au texte, en pixels. Sous cette valeur, une lettre touche le bord.
MARGE_LATERALE_PX = 80

#: Variantes de palette. Elles ne portent **aucune couleur** : elles permutent celles de la
#: charte de la chaîne, qui reste le seul endroit où une couleur se décide. Le référentiel
#: donne bien une palette par niche, mais il le dit lui-même : « intention chromatique, jamais
#: valeur de charte ».
PALETTES: tuple[str, ...] = ("charte", "accent", "inverse")


class MiniatureImpossible(RuntimeError):
    """Aucun fond exploitable, ou Playwright absent : contrat d'entrée non satisfait."""


@dataclass
class Combinaison:
    """Une variante à composer : un texte, un gabarit, une palette."""

    index: int
    texte: str
    gabarit: str
    palette: str
    note_texte: float = 0.5


def couleurs(charte: Charte, palette: str) -> tuple[str, str, str]:
    """`(couleur de la 1re ligne, couleur de la 2e ligne, couleur du bandeau)`."""
    p = charte.palette
    if palette == "accent":
        return p.text, p.accent, p.highlight
    if palette == "inverse":
        return p.highlight, p.text, p.accent
    return p.text, p.highlight, p.accent


def combinaisons(
    textes: list[tuple[str, float]], gabarits: list[str], seed: int, n: int = N_VARIANTES
) -> list[Combinaison]:
    """`n` combinaisons deux à deux distinctes sur `(gabarit, palette)`.

    Avec 2 gabarits et 3 palettes, les couples `(i mod 2, i mod 3)` sont distincts pour
    i = 0, 1, 2 : c'est le tour de passe-passe des restes chinois, et il suffit ici. La graine
    du run décale l'origine pour que deux vidéos de la même chaîne ne sortent pas la même
    miniature (`CONFORMITE` § 5, anti-clonage).
    """
    if not textes:
        raise ValueError("combinaisons : aucun texte de miniature")
    if not gabarits:
        raise ValueError("combinaisons : la charte ne déclare aucun gabarit")
    sorties: list[Combinaison] = []
    for i in range(n):
        texte, note = textes[i % len(textes)]
        sorties.append(Combinaison(
            index=i + 1,
            texte=texte,
            gabarit=gabarits[(seed + i) % len(gabarits)],
            palette=PALETTES[(seed + i) % len(PALETTES)],
            note_texte=note,
        ))
    return sorties


# --------------------------------------------------------------------------------------
# Mesures — couleur
# --------------------------------------------------------------------------------------


def _luminance_relative(rgb: tuple[float, float, float]) -> float:
    """Luminance relative WCAG 2.x d'une couleur sRGB (composantes 0-255)."""
    canaux = []
    for valeur in rgb:
        c = valeur / 255.0
        canaux.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, v, b = canaux
    return 0.2126 * r + 0.7152 * v + 0.0722 * b


def contraste_wcag(couleur_a: tuple[float, float, float],
                   couleur_b: tuple[float, float, float]) -> float:
    """Rapport de contraste WCAG entre deux couleurs, de 1 (identiques) à 21 (noir/blanc)."""
    la, lb = _luminance_relative(couleur_a), _luminance_relative(couleur_b)
    clair, sombre = max(la, lb), min(la, lb)
    return (clair + 0.05) / (sombre + 0.05)


def hex_vers_rgb(couleur: str) -> tuple[float, float, float]:
    """`#101820` → `(16, 24, 32)`."""
    valeur = couleur.lstrip("#")
    return tuple(float(int(valeur[i:i + 2], 16)) for i in (0, 2, 4))  # type: ignore[return-value]


def _vers_lab(rgb: tuple[float, float, float]) -> tuple[float, float, float]:
    """sRGB (0-255) → CIE L*a*b* sous illuminant D65. Vingt lignes, aucune dépendance."""
    lineaire = []
    for valeur in rgb:
        c = valeur / 255.0
        lineaire.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, v, b = lineaire
    x = (0.4124 * r + 0.3576 * v + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * v + 0.0722 * b) / 1.00000
    z = (0.0193 * r + 0.1192 * v + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t + 16 / 116)

    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def distance_lab(couleur_a: tuple[float, float, float],
                 couleur_b: tuple[float, float, float]) -> float:
    """Écart CIE76 entre deux couleurs sRGB. Sous ~15, l'œil ne sépare plus les deux teintes.

    CIE76 et non CIEDE2000 : la formule de 2000 corrige des écarts *faibles* entre couleurs
    voisines, ce qui n'est pas le cas d'usage ici — on veut savoir si un texte se détache d'un
    fond, pas si deux bleus sont assortis. CIEDE2000 exigerait scikit-image, qui n'est pas
    installé.
    """
    la, aa, ba = _vers_lab(couleur_a)
    lb, ab, bb = _vers_lab(couleur_b)
    return math.sqrt((la - lb) ** 2 + (aa - ab) ** 2 + (ba - bb) ** 2)


def couleur_moyenne(image: Path, boite: dict[str, float]) -> tuple[float, float, float]:
    """Couleur moyenne des pixels d'une boîte — ce qu'il y a **derrière** le texte."""
    with Image.open(image) as img:
        cadre = img.convert("RGB").crop(_cadre(boite))
        tableau = np.asarray(cadre, dtype=np.float64)
    if tableau.size == 0:
        return (0.0, 0.0, 0.0)
    moyennes = tableau.reshape(-1, 3).mean(axis=0)
    return (float(moyennes[0]), float(moyennes[1]), float(moyennes[2]))


def couleurs_dominantes(image: Path, boite: dict[str, float], n: int = 3
                        ) -> list[tuple[float, float, float]]:
    """`n` couleurs dominantes du fond sous le texte, par quantification Pillow.

    Pas de k-means : `Image.quantize` fait déjà une partition médiane, elle est déterministe
    et elle ne coûte pas une dépendance de plus pour trois couleurs.
    """
    with Image.open(image) as img:
        cadre = img.convert("RGB").crop(_cadre(boite))
        if cadre.width < 2 or cadre.height < 2:
            return []
        reduit = cadre.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
        palette = reduit.getpalette() or []
        comptes = sorted(reduit.getcolors() or [], key=lambda c: -c[0])
    sorties = []
    for _compte, index in comptes[:n]:
        base = index * 3
        if base + 2 < len(palette):
            sorties.append((float(palette[base]), float(palette[base + 1]),
                            float(palette[base + 2])))
    return sorties


def _cadre(boite: dict[str, float]) -> tuple[int, int, int, int]:
    """Boîte du texte → rectangle de découpe borné à l'image."""
    gauche = max(0, int(boite.get("x", 0)))
    haut = max(0, int(boite.get("y", 0)))
    droite = min(LARGEUR, int(boite.get("x", 0) + boite.get("width", 0)))
    bas = min(HAUTEUR, int(boite.get("y", 0) + boite.get("height", 0)))
    return (gauche, haut, max(gauche + 1, droite), max(haut + 1, bas))


# --------------------------------------------------------------------------------------
# Mesures — lisibilité à la taille d'affichage
# --------------------------------------------------------------------------------------


def vignette(image: Path) -> np.ndarray:
    """L'image ramenée à 168 × 94 px en niveaux de gris, comme le fil mobile l'affiche.

    Rééchantillonnage `BOX` (moyenne de zone) et non `LANCZOS` : c'est le filtre qui
    correspond à ce que fait un navigateur en réduction, et un Lanczos rehausserait les
    contours qu'on cherche justement à mesurer.
    """
    with Image.open(image) as img:
        petite = img.convert("L").resize(
            (LARGEUR_VIGNETTE, HAUTEUR_VIGNETTE), Image.Resampling.BOX
        )
        return np.asarray(petite, dtype=np.float64)


def variance_laplacien(gris: np.ndarray) -> float:
    """Variance du laplacien — netteté des contours. Élevée = contours francs.

    Noyau 4-voisins appliqué en numpy ; `cv2.Laplacian` ferait la même chose, à la
    dépendance près. Sur une vignette de 168 px, un texte qui a fondu au rééchantillonnage
    fait chuter cette variance d'un ordre de grandeur.
    """
    if gris.shape[0] < 3 or gris.shape[1] < 3:
        return 0.0
    centre = gris[1:-1, 1:-1]
    lap = (gris[:-2, 1:-1] + gris[2:, 1:-1] + gris[1:-1, :-2] + gris[1:-1, 2:] - 4 * centre)
    return float(lap.var())


def saillance_residu_spectral(gris: np.ndarray) -> np.ndarray:
    """Carte de saillance par résidu spectral (Hou & Zhang, 2007), en numpy pur.

    Le spectre d'amplitude log d'une image naturelle est presque lisse ; ce qui s'en écarte
    est ce qui attire l'œil. On lisse donc le log-amplitude, on garde le résidu, et on
    repasse en spatial. Vingt lignes contre une dépendance `opencv-contrib` de 50 Mo.
    """
    if gris.size == 0:
        return np.zeros_like(gris)
    spectre = np.fft.fft2(gris)
    amplitude = np.abs(spectre)
    phase = np.angle(spectre)
    log_amplitude = np.log(amplitude + 1e-8)
    # Moyenne glissante 3×3 par convolution séparable, sans scipy.
    lisse = log_amplitude.copy()
    for axe in (0, 1):
        lisse = (np.roll(lisse, 1, axis=axe) + lisse + np.roll(lisse, -1, axis=axe)) / 3.0
    residu = log_amplitude - lisse
    carte = np.abs(np.fft.ifft2(np.exp(residu + 1j * phase))) ** 2
    maximum = carte.max()
    return carte / maximum if maximum > 0 else carte


def part_saillance_sous_texte(gris: np.ndarray, boite: dict[str, float]) -> float:
    """Part de la saillance totale de l'image qui tombe sous le bloc de texte.

    Comparée à la part de **surface** occupée : une valeur bien supérieure à la surface
    signifie que le texte est posé pile sur le sujet. Renvoie une part de saillance, brute ;
    c'est le score composite qui la rapporte à la surface.
    """
    carte = saillance_residu_spectral(gris)
    total = float(carte.sum())
    if total <= 0:
        return 0.0
    echelle_x = LARGEUR_VIGNETTE / LARGEUR
    echelle_y = HAUTEUR_VIGNETTE / HAUTEUR
    x0 = max(0, int(boite.get("x", 0) * echelle_x))
    y0 = max(0, int(boite.get("y", 0) * echelle_y))
    x1 = min(LARGEUR_VIGNETTE, int((boite.get("x", 0) + boite.get("width", 0)) * echelle_x) + 1)
    y1 = min(HAUTEUR_VIGNETTE, int((boite.get("y", 0) + boite.get("height", 0)) * echelle_y) + 1)
    if x1 <= x0 or y1 <= y0:
        return 0.0
    return float(carte[y0:y1, x0:x1].sum() / total)


def mesurer(
    rendu: Path, fond_rendu: Path, boite: dict[str, float], couleur_texte: str,
    couleur_seconde: str,
) -> MesuresMiniature:
    """Les cinq mesures d'une variante, lues sur les deux PNG rendus."""
    if not boite:
        return MesuresMiniature()
    derriere = couleur_moyenne(fond_rendu, boite)
    contraste = contraste_wcag(hex_vers_rgb(couleur_texte), derriere)
    # Le texte est bicolore : le contraste retenu est le pire des deux couleurs employées.
    contraste = min(contraste, contraste_wcag(hex_vers_rgb(couleur_seconde), derriere))

    aire = float(boite.get("aire", 0.0)) or (
        float(boite.get("width", 0.0)) * float(boite.get("height", 0.0))
    )
    surface_pct = 100.0 * aire / (LARGEUR * HAUTEUR)

    # Hauteur d'une **ligne**, pas du bloc : un bloc de deux lignes de 8 px n'est pas lisible
    # parce qu'il mesure 16 px de haut.
    hauteur_ligne = float(boite.get("ligne_min", boite.get("height", 0.0)))
    hauteur_168 = hauteur_ligne * LARGEUR_VIGNETTE / LARGEUR

    # Netteté sur la vignette **entière**, pas sur la seule zone de texte : le texte y occupe
    # un tiers de la surface et domine largement le laplacien — mesuré sur les rendus du run
    # `avwf` (20/09/2026), le fond nu donne 330 quand la miniature complète donne 3 559 à
    # 5 788. C'est donc bien l'apport du texte qu'on lit, sur une zone dont l'échelle est
    # calibrée, plutôt que sur une boîte dont elle ne l'était pas.
    nettete = variance_laplacien(vignette(rendu))

    dominantes = couleurs_dominantes(fond_rendu, boite)
    distance = (
        min(distance_lab(hex_vers_rgb(couleur_texte), d) for d in dominantes)
        if dominantes else None
    )

    return MesuresMiniature(
        contrast_ratio=round(contraste, 2),
        text_area_pct=round(surface_pct, 2),
        text_height_px_168=round(hauteur_168, 2),
        sharpness_168=round(nettete, 1),
        saliency_under_text=round(part_saillance_sous_texte(vignette(fond_rendu), boite), 4),
        palette_distance=None if distance is None else round(distance, 1),
        text_overflow_pct=round(float(boite.get("debordement", 0.0)), 2),
    )


def scorer(mesures: MesuresMiniature, note_texte: float) -> float:
    """Score composite d'une variante, dans [0, 1].

    Cinq termes, et leurs poids disent ce qui décide vraiment. La lisibilité à 168 px pèse le
    plus : une miniature illisible en vignette n'est pas une miniature moyenne, elle n'existe
    pas. Le contraste vient ensuite, plafonné à 7 — au-delà, du blanc sur du noir ne gagne plus
    rien. La surface de texte ne pèse presque rien, et c'est voulu : personne n'a mesuré la
    surface idéale, donc elle ne sert qu'à écarter les deux extrêmes. La saillance sous le
    texte est une **pénalité**, pas un bonus.
    """
    hauteur = mesures.text_height_px_168 or 0.0
    note_lisible = min(1.0, hauteur / max(HAUTEUR_TEXTE_MIN_PX, 1e-6))
    contraste = mesures.contrast_ratio or 0.0
    note_contraste = min(1.0, contraste / 7.0)
    surface = mesures.text_area_pct or 0.0
    # **Garde-fou, pas optimum** : la surface de texte n'a aucune valeur cible mesurée — le
    # référentiel compte des *mots*, pas des pixels. La plage large vient des rendus du run
    # `avwf` (31,5 à 39,1 %) ; elle écarte le texte qui recouvre toute l'image et celui qui
    # disparaît, sans prétendre savoir où se trouve l'optimum. Poids faible en conséquence.
    note_surface = 1.0 if 10.0 <= surface <= 45.0 else max(
        0.0, 1.0 - (10.0 - surface if surface < 10.0 else surface - 45.0) / 20.0
    )
    # Échelle mesurée le 20/09/2026 sur les trois rendus du run `avwf`, vignette 168 px :
    # **3 559 à 5 788 nets**, 476 à 709 après un flou gaussien de 6 px, 330 pour le fond sans
    # texte. On sature à 2 000 — entre le pire net et le meilleur flou — plutôt que de
    # normaliser sur le lot, qui ferait dépendre la note d'une variante des deux autres.
    note_nettete = min(1.0, (mesures.sharpness_168 or 0.0) / 2000.0)
    saillance = mesures.saliency_under_text or 0.0
    surface_relative = surface / 100.0
    # Recouvrir sa propre part de saillance est normal ; en recouvrir trois fois plus veut dire
    # que le texte est sur le sujet.
    penalite = max(0.0, min(0.15, (saillance - 2.0 * surface_relative) * 0.3))

    score = (0.32 * note_lisible + 0.26 * note_contraste + 0.08 * note_surface
             + 0.13 * note_nettete + 0.21 * max(0.0, min(1.0, note_texte)) - penalite)
    if contraste and contraste < CONTRASTE_MIN:
        score *= 0.75          # sous le seuil WCAG : pénalisée, pas éliminée — il en faut trois
    if hauteur and hauteur < HAUTEUR_TEXTE_MIN_PX:
        score *= 0.75
    if (mesures.text_overflow_pct or 0.0) > 0.5:
        score *= 0.5           # une lettre coupée n'est pas un défaut de degré : elle se voit
    return round(max(0.0, min(1.0, score)), 3)


def alertes_de(variante: VarianteMiniature, mesures: MesuresMiniature) -> list[str]:
    """Ce qu'une variante mesurée oblige à dire à l'humain, en clair."""
    dits: list[str] = []
    nom = Path(variante.file).name
    if mesures.contrast_ratio is not None and mesures.contrast_ratio < CONTRASTE_MIN:
        dits.append(f"{nom} : contraste {mesures.contrast_ratio:.2f} sous le seuil WCAG "
                    f"de {CONTRASTE_MIN}")
    if (mesures.text_height_px_168 or 0.0) < HAUTEUR_TEXTE_MIN_PX:
        dits.append(f"{nom} : texte de {mesures.text_height_px_168:.1f} px une fois réduit à "
                    f"{LARGEUR_VIGNETTE} px, pour {HAUTEUR_TEXTE_MIN_PX:.0f} exigés")
    if mesures.palette_distance is not None and mesures.palette_distance < 15.0:
        dits.append(f"{nom} : écart de couleur {mesures.palette_distance:.0f} (L*a*b*) avec le "
                    "fond — le texte s'y fond malgré le contraste de luminance")
    if (mesures.text_overflow_pct or 0.0) > 0.5:
        dits.append(f"{nom} : {mesures.text_overflow_pct:.1f} % du texte hors du cadre — "
                    "la réduction automatique de police n'a pas suffi")
    return dits


# --------------------------------------------------------------------------------------
# Rotation
# --------------------------------------------------------------------------------------

#: Jours après publication avant d'envisager la bascule. **Paramètre, pas vérité mesurée.**
#: Le prompt de l'étape 21 fixe 7 jours ; la pratique décrite par les blogs de créateurs
#: conseille d'attendre 30 jours (phase de découverte). Aucune source officielle YouTube ne
#: tranche. 7 est retenu parce que la Reporting API a 72 h de latence et que la rétention des
#: rapports « reach » est de 30 à 60 jours : attendre un mois ferait mesurer une bascule sur
#: des données en train d'expirer. À réarbitrer à la phase 5, sur le CTR réel.
ROTATION_APRES_JOURS = 7
CRITERE_ROTATION = (
    "CTR de la vidéo sous la médiane de la chaîne sur les 7 derniers jours (Reporting API, "
    "rapport « reach ») et au moins 1 000 impressions cumulées"
)


# --------------------------------------------------------------------------------------
# Composition et rendu
# --------------------------------------------------------------------------------------


def decouper(texte: str) -> list[str]:
    """Deux lignes au plus : la seconde porte l'accent de couleur."""
    mots = texte.split()
    if len(mots) <= 2:
        return mots or [texte]
    coupe = (len(mots) + 1) // 2
    return [" ".join(mots[:coupe]), " ".join(mots[coupe:])]


def html_miniature(
    texte: str, fond: Path, charte: Charte, gabarit: str, palette: str, police: Path,
    bandeau: str, avec_texte: bool,
) -> str:
    """Page de composition. `avec_texte=False` sert à mesurer ce qu'il y a derrière le texte."""
    lignes = decouper(texte.upper() if charte.thumbnail.uppercase else texte)
    plus_long = max((len(ligne) for ligne in lignes), default=1)
    # La taille est déduite de la ligne la plus longue pour que le texte occupe la largeur
    # sans déborder : 1280 px de large, ~0,56 em par caractère en Inter très grasse.
    taille = int(min(200, max(84, (LARGEUR - 160) / max(plus_long, 1) / 0.56)))
    premiere, seconde, accent = couleurs(charte, palette)
    corps = "".join(
        f'<span class="l{i}">{ligne}</span>' for i, ligne in enumerate(lignes)
    ) if avec_texte else ""
    position = ("justify-content:flex-end;align-items:center;padding-bottom:150px"
                if gabarit == "bandeau_bas"
                else "justify-content:center;align-items:flex-start;padding-left:64px;"
                     "text-align:left")
    alignement = "center" if gabarit == "bandeau_bas" else "left"
    return f"""<!doctype html><meta charset="utf-8">
<style>
@font-face {{ font-family:'ChartePolice'; src:url('{police.as_uri()}'); }}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{width:{LARGEUR}px;height:{HAUTEUR}px;position:relative;overflow:hidden;
 background:{charte.palette.bg};font-family:'ChartePolice',Arial,sans-serif}}
.bg{{position:absolute;inset:0;background:url('{fond.as_uri()}') center/cover;
 filter:brightness({charte.thumbnail.fond_luminosite}) saturate(1.15)}}
.voile{{position:absolute;inset:0;background:linear-gradient(
 {"180deg, rgba(0,0,0,0) 35%, rgba(0,0,0,.72) 100%" if gabarit == "bandeau_bas"
   else "90deg, rgba(0,0,0,.78) 0%, rgba(0,0,0,.15) 72%"})}}
.bandeau{{position:absolute;{"left:0;right:0;bottom:0;height:88px" if gabarit == "bandeau_bas"
 else "left:0;top:0;bottom:0;width:18px"};background:{accent}}}
#texte{{position:absolute;inset:0;display:flex;flex-direction:column;{position};
 text-align:{alignement};gap:2px}}
#texte span{{font-size:{taille}px;font-weight:800;line-height:.96;color:{premiere};
 letter-spacing:-2px;-webkit-text-stroke:{max(3, taille // 22)}px {charte.palette.text_outline};
 paint-order:stroke fill;text-shadow:0 10px 30px rgba(0,0,0,.9)}}
#texte span.l1{{color:{seconde}}}
.tag{{position:absolute;{"left:36px;bottom:20px" if gabarit == "bandeau_bas"
 else "right:36px;top:28px"};font-size:34px;font-weight:800;letter-spacing:3px;
 color:{charte.palette.bg if gabarit == "bandeau_bas" else accent};
 text-transform:uppercase}}
</style>
<div class="bg"></div><div class="voile"></div><div class="bandeau"></div>
<div id="texte">{corps}</div><div class="tag">{bandeau}</div>"""


#: Ajustement avant capture : réduit la police tant qu'une ligne dépasse la largeur utile.
#:
#: La taille est d'abord déduite du nombre de caractères (~0,56 em par caractère en Inter très
#: grasse), ce qui est une **approximation** : « STRETCHING », dix caractères larges, sortait du
#: cadre par la droite sur le run `avwf` (20/09/2026) alors que toutes les mesures de la
#: variante étaient bonnes. Le navigateur, lui, connaît la largeur réelle une fois la police
#: chargée. On la lui demande, plutôt que d'affiner un coefficient au jugé.
_AJUSTER_JS = """(marge) => {
 const spans = [...document.querySelectorAll('#texte span')];
 if (!spans.length) return 0;
 const utile = document.body.clientWidth - marge;
 let reductions = 0;
 for (let i = 0; i < 40; i++) {
   const trop = spans.some(s => s.getBoundingClientRect().width > utile);
   if (!trop) break;
   for (const s of spans) {
     const taille = parseFloat(getComputedStyle(s).fontSize);
     s.style.fontSize = (taille * 0.96) + 'px';
   }
   reductions += 1;
 }
 return reductions;
}"""

#: Ce que la page mesure sur elle-même, une fois les polices chargées. `ligne_min` est la
#: hauteur de la **plus petite ligne** : c'est elle qui décide de la lisibilité en vignette,
#: pas la hauteur du bloc, qu'un empilement de deux lignes minuscules gonflerait. `debordement`
#: est la part de largeur qui sortirait encore du cadre — zéro après ajustement, sauf si les
#: quarante réductions n'ont pas suffi.
_MESURE_JS = """() => {
 const spans = [...document.querySelectorAll('#texte span')];
 if (!spans.length) return null;
 const r = spans.map(s => s.getBoundingClientRect());
 const x = Math.min(...r.map(b => b.left)), y = Math.min(...r.map(b => b.top));
 const w = Math.max(...r.map(b => b.right)) - x;
 const h = Math.max(...r.map(b => b.bottom)) - y;
 const aire = r.reduce((a, b) => a + b.width * b.height, 0);
 const ligne_min = Math.min(...r.map(b => b.height));
 const large = document.body.clientWidth;
 const hors = r.reduce((a, b) => a + Math.max(0, b.right - large) + Math.max(0, -b.left), 0);
 const debordement = 100 * hors / r.reduce((a, b) => a + b.width, 1);
 return {x, y, width: w, height: h, aire, ligne_min, debordement};
}"""


def rendre_lot(pages: list[tuple[Path, Path, bool]]) -> list[dict[str, Any]]:
    """Capture toutes les pages en **un seul navigateur**. Renvoie une boîte par page.

    Un `sync_playwright()` par capture coûtait 0,24 s de lancement à chaque fois (mesure de
    l'étape 4) ; six captures par run, c'est une seconde et demie payée pour rien. Le
    navigateur est lancé une fois, les pages défilent dedans.
    """
    from factory.doctor import charge_env

    # Le cache du navigateur est imposé ici, pas espéré du shell : lancé sans cette variable,
    # Playwright retélécharge 0,21 Go dans ~/Library/Caches (étape 13.2, même défaut que mflux).
    charge_env()
    from playwright.sync_api import sync_playwright

    boites: list[dict[str, Any]] = []
    with sync_playwright() as pw:
        navigateur = pw.chromium.launch()
        page = navigateur.new_page(viewport={"width": LARGEUR, "height": HAUTEUR})
        for source, sortie, mesurer_page in pages:
            page.goto(source.as_uri())
            page.wait_for_function("document.fonts.ready")
            if mesurer_page:
                page.evaluate(_AJUSTER_JS, MARGE_LATERALE_PX)
                boites.append(page.evaluate(_MESURE_JS) or {})
            else:
                boites.append({})
            page.screenshot(path=str(sortie))
        navigateur.close()
    return boites


def alleger(fichier: Path) -> tuple[float, bool]:
    """Ramène le PNG sous 2 Mo par quantification si nécessaire. Renvoie `(Mo, allégé)`."""
    mo = fichier.stat().st_size / 1e6
    if mo <= POIDS_MAX_MO:
        return round(mo, 3), False
    with Image.open(fichier) as img:
        img.convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT).save(
            fichier, optimize=True
        )
    return round(fichier.stat().st_size / 1e6, 3), True


def phash(fichier: Path) -> str:
    """Empreinte perceptuelle — alimente `dedupe_hash.thumbnail_phash` (CONFORMITE § 5)."""
    import imagehash

    with Image.open(fichier) as img:
        return str(imagehash.phash(img.convert("RGB")))


def composer(
    combos: list[Combinaison], fond: Path, charte: Charte, bandeau: str, police: Path,
    dossier: Path, travail: Path, prefixe: str = "variant",
) -> tuple[list[VarianteMiniature], list[str]]:
    """Compose et mesure toutes les variantes. Renvoie `(variantes triées, alertes)`.

    Deux pages par variante : l'une avec le texte, l'autre sans — c'est la seconde qui donne
    les pixels réellement situés derrière le texte, donc le contraste vrai. Les six captures
    partent dans un seul navigateur.
    """
    travail.mkdir(parents=True, exist_ok=True)
    dossier.mkdir(parents=True, exist_ok=True)
    pages: list[tuple[Path, Path, bool]] = []
    sorties: list[tuple[Combinaison, Path, Path]] = []
    for combo in combos:
        sortie = dossier / f"{prefixe}_{combo.index}.png"
        fond_rendu = travail / f"{sortie.stem}_fond.png"
        page = travail / f"{sortie.stem}.html"
        page_nue = travail / f"{sortie.stem}_fond.html"
        page.write_text(
            html_miniature(combo.texte, fond, charte, combo.gabarit, combo.palette, police,
                           bandeau, True), encoding="utf-8")
        page_nue.write_text(
            html_miniature(combo.texte, fond, charte, combo.gabarit, combo.palette, police,
                           bandeau, False), encoding="utf-8")
        pages.append((page, sortie, True))
        pages.append((page_nue, fond_rendu, False))
        sorties.append((combo, sortie, fond_rendu))

    boites = rendre_lot(pages)
    variantes: list[VarianteMiniature] = []
    alertes: list[str] = []
    for position, (combo, sortie, fond_rendu) in enumerate(sorties):
        boite = boites[position * 2]
        premiere, seconde, _accent = couleurs(charte, combo.palette)
        if not boite:
            alertes.append(f"{sortie.name} : aucun texte mesuré sur la page rendue")
        mesures = mesurer(sortie, fond_rendu, boite, premiere, seconde)
        mo, allege = alleger(sortie)
        if allege:
            alertes.append(f"{sortie.name} : quantifié en 256 couleurs pour passer sous 2 Mo")
        hauteur_ratio = float(boite.get("height", 0.0)) / HAUTEUR
        variante = VarianteMiniature(
            file=f"thumbnails/{sortie.name}",
            text=combo.texte,
            template=combo.gabarit,
            palette=combo.palette,
            measures=mesures,
            contrast_ratio=mesures.contrast_ratio,
            text_area_ratio=round((mesures.text_area_pct or 0.0) / 100.0, 4),
            text_height_ratio=round(hauteur_ratio, 4),
            legible_at_320px=(
                (mesures.text_height_px_168 or 0.0) >= HAUTEUR_TEXTE_MIN_PX
                and (mesures.contrast_ratio or 0.0) >= CONTRASTE_MIN
            ),
            phash=phash(sortie),
            score=scorer(mesures, combo.note_texte),
        )
        seuil = charte.thumbnail.hauteur_texte_min
        if hauteur_ratio < seuil:
            alertes.append(f"{sortie.name} : bloc de texte à {hauteur_ratio:.1%} de la hauteur "
                           f"pour {seuil:.0%} exigés par la charte")
        alertes += alertes_de(variante, mesures)
        variantes.append(variante)

    variantes.sort(key=lambda v: -(v.score or 0.0))
    return variantes, alertes


# --------------------------------------------------------------------------------------
# Étape 26 — politique de Thompson (learned/weights.json → thumbnail_policy)
# --------------------------------------------------------------------------------------


def _beta(politique: dict[str, Any], gabarit: str | None) -> tuple[float, float]:
    """Paramètres Beta d'un gabarit ; a priori de la chaîne s'il n'a jamais été montré."""
    prior = politique.get("prior") or {}
    ctr, force = float(prior.get("ctr", 0.04)), float(prior.get("strength", 200.0))
    t = (politique.get("templates") or {}).get(gabarit or "") or {}
    return float(t.get("alpha", ctr * force)), float(t.get("beta", (1 - ctr) * force))


def choisir_initiale(variantes: list[VarianteMiniature], poids: dict[str, Any] | None,
                     seed: int) -> tuple[VarianteMiniature, str]:
    """Variante initiale : score composite, ou tirage de Thompson si la politique est active.

    Thompson ne départage que les variantes lisibles à 320 px (le banc garde la main sur la
    lisibilité) ; tirage seedé, donc rejouable. Politique inactive (n < seuil) → score.
    """
    politique = (poids or {}).get("thumbnail_policy") or {}
    if not politique.get("active") or not variantes:
        return variantes[0], "score composite le plus élevé"
    candidates = [v for v in variantes if v.legible_at_320px] or variantes
    alea = np.random.default_rng(seed)
    tirages = [(float(alea.beta(*_beta(politique, v.template))), v) for v in candidates]
    theta, gagnante = max(tirages, key=lambda tv: tv[0])
    return gagnante, f"Thompson : θ tiré {theta:.4f} pour le gabarit {gagnante.template}"


def proposer_rotation(ctr_7d: float | None, ctr_mediane: float | None,
                      suivantes: list[tuple[str, str | None]], poids: dict[str, Any] | None,
                      seed: int) -> tuple[str | None, str]:
    """(variante proposée, motif) pour la rotation J+7 ; `None` si rien à faire.

    Critère : CTR J+7 sous la médiane CTR de la chaîne. Parmi les variantes restantes, tirage
    de Thompson si la politique existe, sinon la suivante dans l'ordre du score.
    """
    if ctr_7d is None or ctr_mediane is None:
        return None, "CTR J+7 ou médiane de la chaîne indisponible (rapports reach)"
    if ctr_7d >= ctr_mediane:
        return None, f"CTR {ctr_7d:.2%} ≥ médiane {ctr_mediane:.2%} : on garde"
    if not suivantes:
        return None, "aucune variante restante"
    politique = (poids or {}).get("thumbnail_policy") or {}
    if not politique:
        return suivantes[0][0], f"CTR {ctr_7d:.2%} < médiane {ctr_mediane:.2%} : variante suivante"
    alea = np.random.default_rng(seed)
    tirages = [(float(alea.beta(*_beta(politique, g))), s) for s, g in suivantes]
    theta, choisie = max(tirages)
    return choisie, f"CTR {ctr_7d:.2%} < médiane {ctr_mediane:.2%} : Thompson θ={theta:.4f}"
