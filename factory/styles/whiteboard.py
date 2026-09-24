"""Moteur « whiteboard animé » — un dessin au trait se trace sous une main qui le suit.

Le style tient en quatre gestes, et aucun n'est une image animée : tout est vectoriel une fois
le dessin obtenu.

1. **Une image au trait par plan.** Le modèle d'image reçoit un prompt de style qui lui est
   propre — « clean black line art on white background, no shading, no text » — et non le
   `style_prefix` de la charte, qui décrit une illustration en aplats de couleur. La
   bibliothèque de `factory/assets/images.py` sert de cache : la clé porte le style, donc une
   image d'illustration ne peut pas être resservie ici, ni l'inverse.
2. **Vectorisation par vtracer** (MIT, jamais potrace qui est GPL). Le trait noir devient une
   suite de contours fermés. Un contour = un geste de dessin.
3. **Un ordre de dessin plausible.** Les gros éléments d'abord, puis les détails, chaque groupe
   balayé de haut-gauche vers bas-droite. C'est l'ordre dans lequel une main dessine, et c'est
   le seul endroit où ce moteur invente quelque chose.
4. **Le tracé.** La scène `draw-svg` allonge chaque contour à la vitesse voulue, pose la main à
   l'extrémité courante, puis fait monter le remplissage derrière elle.

**Le plafond de chemins est une contrainte dure** (`ROADMAP` § Étape 30.2) : au-delà de 400
contours, l'animation devient un fourmillement illisible et le navigateur peine. Le moteur
re-simplifie alors, d'un cran de `filter_speckle` à la fois, et **journalise chaque image** avec
le compte obtenu et le réglage qui l'a produit.

Ce que le moteur ne fait pas : il ne connaît ni la langue, ni la conformité, ni le montage. La
phrase de divulgation lui est passée (`texte_divulgation`), les horodatages viennent de
`words.json`, les couleurs de marqueur viennent de la charte.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

import vtracer

from factory import video
from factory.assets import images as assets_images
from factory.core import db
from factory.core.models import Asset, Channel, Shot, Shotlist
from factory.core.paths import RunPaths
from factory.styles.revideo import MoteurRevideo, RenduRevideoEchoue

#: Prompt de style du whiteboard. Il remplace `charte.style_prefix` — qui décrit, sur toutes les
#: chaînes livrées, une illustration en aplats de couleur, c'est-à-dire l'inverse de ce que
#: vtracer sait vectoriser. C'est le seul style dont l'image ne vient pas de la charte, et le
#: motif est écrit ici pour qu'on n'aille pas le « corriger » plus tard.
PROMPT_STYLE = (
    "clean black line art on white background, no shading, no text, no labels, "
    "single weight ink outline drawing, bold clear contours, no hatching, no gradient, "
    "no grey tones, simple iconic shapes, generous empty white space, centred composition"
)

#: Plafond de contours par image. Au-delà, le dessin fourmille et le tracé devient illisible.
PLAFOND_CHEMINS = 400

#: Échelle de simplification de vtracer, du plus fin au plus grossier. Le moteur descend cette
#: échelle tant que le plafond n'est pas tenu ; le dernier cran tient toujours, parce qu'il ne
#: garde que des taches de plus de 4 096 pixels.
ECHELONS_SIMPLIFICATION: tuple[dict[str, int], ...] = (
    {"filter_speckle": 4, "length_threshold": 4, "corner_threshold": 60},
    {"filter_speckle": 8, "length_threshold": 6, "corner_threshold": 65},
    {"filter_speckle": 16, "length_threshold": 10, "corner_threshold": 70},
    {"filter_speckle": 40, "length_threshold": 14, "corner_threshold": 75},
    {"filter_speckle": 96, "length_threshold": 20, "corner_threshold": 80},
    {"filter_speckle": 256, "length_threshold": 28, "corner_threshold": 85},
)

#: Résolution de génération. 768×768 et non 1280×720 : l'image n'est pas montrée, elle est
#: **vectorisée**, et un contour tracé à 768 px se rend aussi net à 1080p qu'un contour tracé à
#: 1280 px. Mesuré le 19/09/2026 sur cette machine : 63,6 s contre 137,0 s, soit 54 % du coût
#: pour un nombre de contours inchangé.
RESOLUTION = "768x768"

#: Sous ce nombre de contours, le dessin se trace en un ou deux gestes. Ce n'est pas un échec —
#: mesuré le 19/09/2026, plusieurs plans du lot sortent à 2 ou 3 contours avec une encre normale
#: (2 % du cadre) : le sujet est simplement une forme d'un seul tenant. C'est un **avertissement**
#: au journal, pas une condition de repli.
PLANCHER_CHEMINS = 3

#: Part de la durée du plan consacrée au tracé. Les 20 % restants laissent le dessin fini à
#: l'écran — sans ce temps mort, la coupe tombe sur le dernier trait et rien ne se lit.
PART_TRACE = 0.80

#: Aire de boîte englobante, en part de l'image, au-delà de laquelle un contour est « gros ».
SEUIL_GROS_ELEMENT = 0.012

#: Hauteur d'une bande de balayage, en part de l'image. Deux contours de la même bande se
#: dessinent de gauche à droite ; c'est ce qui fait lire l'ordre comme une main et non comme un
#: tri par taille.
HAUTEUR_BANDE = 0.22

#: Licence des deux mains. Elles sont tracées par `outils/mains_whiteboard.py`, donc à nous.
LICENCE_MAIN = "CC0-1.0"

NOMBRE_SVG = re.compile(r"-?\d+(?:\.\d+)?")


class DessinIndisponible(RuntimeError):
    """Aucun contour exploitable n'a pu être tiré de l'image d'un plan."""


def prompt_whiteboard(channel: Channel, intention: str, rupture: bool = False) -> str:
    """`PROMPT_STYLE` + intention (+ cadrage de rupture). La charte n'entre pas ici.

    Signature alignée sur `assets_images.construire_prompt` : c'est ce que `GenerateurImages`
    appelle. `channel` n'est pas lu — et ce n'est pas un oubli : deux chaînes en whiteboard
    doivent produire le **même** dessin pour la même intention, sinon la bibliothèque ne sert
    jamais deux fois.
    """
    morceaux = [PROMPT_STYLE, intention.strip().rstrip(".")]
    if rupture:
        morceaux.append("wide establishing framing, more of the scene visible")
    return ", ".join(m for m in morceaux if m)


def _sous_chemins(donnees: str) -> list[str]:
    """Découpe l'attribut `d` d'un chemin vtracer en contours fermés, un par commande `M`.

    vtracer rend **un** `<path>` par couleur, dont le `d` enchaîne tous les contours de cette
    couleur. Un contour est l'unité de geste : c'est lui qu'on trace, qu'on ordonne et que la
    main suit. Sans cette découpe, une image entière est un seul trait de dix secondes.
    """
    morceaux = [m.strip() for m in re.split(r"(?=M)", donnees) if m.strip()]
    return [m for m in morceaux if m.startswith("M")]


def _translater(contour: str, tx: float, ty: float) -> str:
    """Rebat le `transform="translate(x,y)"` de vtracer dans les coordonnées du contour.

    vtracer sort **un `<path>` par tache**, chacun posé par une translation et dont le `d` est
    exprimé depuis son coin. Sans ce rabattage, tous les contours d'une image se superposent à
    l'origine : le dessin est illisible et l'ordre de tracé ne veut plus rien dire. Le piège a
    coûté un rendu, il est écrit ici.

    Les commandes de vtracer sont `M`, `C` et `Z`, toutes absolues et toutes en paires de
    coordonnées : translater chaque paire suffit, il n'y a pas de commande à un seul nombre
    (`H`, `V`) ni d'arc (`A`, dont deux nombres sont des rayons et un un angle).
    """
    index = {"n": 0}

    def remplacer(m: re.Match[str]) -> str:
        decalage = tx if index["n"] % 2 == 0 else ty
        index["n"] += 1
        return f"{float(m.group(0)) + decalage:.2f}".rstrip("0").rstrip(".")

    # `:.2f` garantit un point décimal, donc `rstrip("0")` ne peut pas amputer un entier.
    return NOMBRE_SVG.sub(remplacer, contour)


def _boite(contour: str) -> tuple[float, float, float, float]:
    """Boîte englobante approchée d'un contour : tous ses nombres lus comme des paires x, y.

    Approchée, parce que les points de contrôle des cubiques sortent parfois de la boîte réelle.
    L'usage est un **tri**, pas un cadrage : une boîte un peu large ne change pas l'ordre.
    """
    nombres = [float(n) for n in NOMBRE_SVG.findall(contour)]
    xs, ys = nombres[0::2], nombres[1::2]
    if not xs or not ys:
        return (0.0, 0.0, 0.0, 0.0)
    return (min(xs), min(ys), max(xs), max(ys))


def _longueur(contour: str) -> float:
    """Longueur approchée : la somme des sauts entre points cités. Sert à répartir le temps."""
    nombres = [float(n) for n in NOMBRE_SVG.findall(contour)]
    points = list(zip(nombres[0::2], nombres[1::2]))
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        total += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    return total


def ordonner(
    contours: list[tuple[int, str]], largeur: float, hauteur: float
) -> list[tuple[int, str]]:
    """Ordre de dessin plausible : les gros éléments d'abord, chacun balayé haut-gauche → bas-droite.

    Deux groupes, et non un tri unique par taille : un tri par taille seul fait sauter la main
    d'un bout à l'autre du cadre à chaque contour. Ici la main pose d'abord la structure, puis
    revient remplir les détails, et à l'intérieur de chaque passe elle descend la page.
    """
    aire_image = max(1.0, largeur * hauteur)
    bande = max(1.0, hauteur * HAUTEUR_BANDE)

    def cle(entree: tuple[int, str]) -> tuple[int, int, float, float]:
        x0, y0, x1, y1 = _boite(entree[1])
        aire = max(0.0, (x1 - x0) * (y1 - y0)) / aire_image
        groupe = 0 if aire >= SEUIL_GROS_ELEMENT else 1
        return (groupe, int(y0 // bande), x0, y0)

    return sorted(contours, key=cle)


def _boite_totale(contours: list[str], largeur: int, hauteur: int) -> list[float]:
    """Boîte de l'encre, bornée à la toile. Toile entière si aucun contour n'a été tiré."""
    if not contours:
        return [0.0, 0.0, float(largeur), float(hauteur)]
    boites = [_boite(c) for c in contours]
    return [
        max(0.0, min(b[0] for b in boites)), max(0.0, min(b[1] for b in boites)),
        min(float(largeur), max(b[2] for b in boites)),
        min(float(hauteur), max(b[3] for b in boites)),
    ]


def _groupes(ordonnes: list[tuple[int, str]], elements: list[str]) -> list[dict]:
    """Un remplissage par `<path>` de vtracer, et le rang de ses contours dans l'ordre de tracé.

    Le remplissage n'apparaît qu'une fois **tous** ses contours tracés : sans cela, l'anneau
    extérieur d'une forme se remplirait avant que son trou soit dessiné, et la forme clignoterait.
    """
    membres: dict[int, list[int]] = {}
    for rang, (element, _) in enumerate(ordonnes):
        membres.setdefault(element, []).append(rang)
    return [
        {"d": elements[element], "membres": rangs}
        for element, rangs in sorted(membres.items())
    ]


@dataclass
class ResultatTrace:
    """Ce que la vectorisation d'une image a produit, et ce qu'elle a coûté."""

    contours: list[str]
    #: Remplissages, un par `<path>` de vtracer : `{"d", "membres"}`. Un groupe garde la règle
    #: de remplissage de vtracer — trous compris. Découpé en contours, un anneau deviendrait un
    #: disque, et le dessin une tache noire (mesuré au premier rendu du 19/09).
    groupes: list[dict]
    #: Boîte de l'encre `[x0, y0, x1, y1]` dans la toile. Cadrer sur la toile 768×768 laissait le
    #: dessin occuper 39 % de la largeur utile, marges blanches du modèle comprises (mesuré le
    #: 19/09/2026) : c'est la boîte de l'encre qui remplit le cadre, pas la toile.
    boite: list[float]
    largeur: int
    hauteur: int
    echelon: int
    reglage: dict[str, int]
    essais: int
    secondes: float


def vectoriser(
    png: Path, svg: Path, plafond: int = PLAFOND_CHEMINS
) -> ResultatTrace:
    """PNG au trait → contours SVG ordonnés, sous le plafond de chemins.

    Le mode est `binary` + `cutout` : le dessin est noir sur blanc, il n'y a qu'une couleur à
    tracer, et les trous (l'intérieur des boucles) doivent être découpés et non empilés. `spline`
    rend des cubiques, donc un trait qui s'allonge proprement plutôt qu'une ligne brisée.
    """
    depart = time.perf_counter()
    dernier: list[str] = []
    for echelon, reglage in enumerate(ECHELONS_SIMPLIFICATION):
        vtracer.convert_image_to_svg_py(
            str(png), str(svg), colormode="binary", hierarchical="cutout", mode="spline",
            splice_threshold=45, path_precision=2, **reglage,
        )
        texte = svg.read_text(encoding="utf-8")
        largeur = int(float(re.search(r'width="(\d+(?:\.\d+)?)"', texte).group(1)))
        hauteur = int(float(re.search(r'height="(\d+(?:\.\d+)?)"', texte).group(1)))
        contours: list[tuple[int, str]] = []
        elements: list[str] = []
        for balise in re.findall(r"<path\b[^>]*/?>", texte):
            donnees = re.search(r'\sd="([^"]+)"', balise)
            if donnees is None:
                continue
            translation = re.search(
                r'transform="translate\(\s*(-?[\d.]+)\s*,\s*(-?[\d.]+)\s*\)"', balise
            )
            tx, ty = (
                (float(translation.group(1)), float(translation.group(2)))
                if translation else (0.0, 0.0)
            )
            complet = donnees.group(1)
            if tx or ty:
                complet = _translater(complet, tx, ty)
            element = len(elements)
            elements.append(complet)
            for contour in _sous_chemins(complet):
                contours.append((element, contour))
        dernier, derniers_elements = contours, elements
        if len(contours) <= plafond:
            ordonnes = ordonner(contours, largeur, hauteur)
            return ResultatTrace(
                contours=[c for _, c in ordonnes],
                groupes=_groupes(ordonnes, elements),
                boite=_boite_totale([c for _, c in ordonnes], largeur, hauteur),
                largeur=largeur, hauteur=hauteur,
                echelon=echelon, reglage=reglage, essais=echelon + 1,
                secondes=time.perf_counter() - depart,
            )
    # Le dernier échelon n'a pas tenu : on coupe aux `plafond` contours les plus longs. Un
    # dessin amputé vaut mieux qu'un plan qui fait tomber le run.
    garde = sorted(dernier, key=lambda e: _longueur(e[1]), reverse=True)[:plafond]
    ordonnes = ordonner(garde, largeur, hauteur)
    return ResultatTrace(
        contours=[c for _, c in ordonnes],
        groupes=_groupes(ordonnes, derniers_elements),
        boite=_boite_totale([c for _, c in ordonnes], largeur, hauteur),
        largeur=largeur, hauteur=hauteur,
        echelon=len(ECHELONS_SIMPLIFICATION) - 1, reglage=ECHELONS_SIMPLIFICATION[-1],
        essais=len(ECHELONS_SIMPLIFICATION) + 1, secondes=time.perf_counter() - depart,
    )


@dataclass
class WhiteboardEngine(MoteurRevideo):
    """Moteur de style « whiteboard » (`STYLE_ENGINES["whiteboard"]`)."""

    name: str = "whiteboard"
    backend: str = "revideo"
    conn: sqlite3.Connection | None = None
    #: Contours par plan, relevés par `prepare_assets` pour la ligne de journal du plafond.
    plafond_journal: list[dict] = field(default_factory=list)

    # -- paramètres ----------------------------------------------------------------------

    @property
    def resolution(self) -> str:
        return str(self.param("image.resolution", RESOLUTION) or RESOLUTION)

    @property
    def modele_image(self) -> str:
        return str(self.param("image.model", assets_images.MODELE_DEFAUT)
                   or assets_images.MODELE_DEFAUT)

    @property
    def etapes(self) -> int:
        return int(self.param("image.steps", assets_images.ETAPES_DEFAUT)
                   or assets_images.ETAPES_DEFAUT)

    @property
    def plafond_chemins(self) -> int:
        return int(self.param("trace.plafond_chemins", PLAFOND_CHEMINS) or PLAFOND_CHEMINS)

    @property
    def part_trace(self) -> float:
        return float(self.param("draw.part_trace", PART_TRACE) or PART_TRACE)

    @property
    def police_manuscrite(self) -> video.Police:
        """Police manuscrite OFL du style — jamais une police système."""
        return video.resoudre_police(
            str(self.param("draw.police", "Caveat SemiBold") or "Caveat SemiBold"), self.racine
        )

    def mains(self) -> list[dict]:
        """Les deux mains, en URI de données : Vite n'a alors rien à servir depuis le disque."""
        import base64

        sorties: list[dict] = []
        for relatif in self.param("draw.mains", ["assets/charte/main.png",
                                                 "assets/charte/main_2.png"]) or []:
            chemin = self.racine / str(relatif)
            if not chemin.exists():
                raise FileNotFoundError(
                    f"main absente : {chemin} — régénère-la avec "
                    "`uv run python outils/mains_whiteboard.py`"
                )
            donnees = base64.b64encode(chemin.read_bytes()).decode("ascii")
            largeur, hauteur = video.taille_png(chemin)
            sorties.append({
                "src": f"data:image/png;base64,{donnees}",
                "width": largeur, "height": hauteur,
                # Pointe du feutre dans la planche, en part de la largeur et de la hauteur.
                "tip": [
                    float(self.param("draw.pointe_x", 44) or 44) / largeur,
                    float(self.param("draw.pointe_y", 40) or 40) / hauteur,
                ],
            })
        if not sorties:
            raise FileNotFoundError("aucune main déclarée dans config/styles/whiteboard.yaml")
        return sorties

    # -- assets --------------------------------------------------------------------------

    def _mots_du_plan(self, mots: list[dict], shot: Shot) -> list[dict]:
        """Les mots prononcés pendant le plan, réexprimés depuis son début."""
        return [
            {"w": str(m.get("word", "")).strip(), "t": round(float(m["start"]) - shot.start_s, 3),
             "e": round(float(m["end"]) - shot.start_s, 3)}
            for m in mots
            if float(m.get("start", -1)) >= shot.start_s - 1e-6
            and float(m.get("end", -1)) <= shot.end_s + 1e-6
            and str(m.get("word", "")).strip()
        ]

    def prepare_assets(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths
    ) -> list[Asset]:
        """Une image au trait par plan, sa vectorisation, sa spec de scène — puis tout le rendu.

        Comme pour le moteur motion design, **tout** le rendu a lieu ici : un lancement de
        Chromium coûte une dizaine de secondes, le payer une fois pour vingt plans est le premier
        levier de vitesse. `render_shot` ne fait plus que constater, ou réparer un plan manquant.
        """
        self.verifier_render()
        self.conn = db.ouvrir(self.racine / "workspace" / "factory.db")
        generateur = assets_images.GenerateurImages(
            conn=self.conn, style_id=self.style.id, racine=self.racine, journal=self.journal,
            modele=self.modele_image, resolution=self.resolution, etapes=self.etapes,
            constructeur_prompt=prompt_whiteboard,
        )
        # Le LLM d'abord, seul, puis mflux, seul : jamais deux modèles résidents
        # (`ARCHITECTURE` § 1.3). La traduction est vide sur une chaîne anglophone.
        generateur.traductions = assets_images.traduire_intentions(
            [s.asset_request.prompt_or_keywords for s in shotlist.shots],
            channel.lang, racine=self.racine, journal=self.journal,
        )

        t_assets = time.perf_counter()
        assets: list[Asset] = []
        traces: dict[str, ResultatTrace] = {}
        generees = reutilisees = 0
        secondes_trace = 0.0
        for shot in shotlist.shots:
            dossier = run.asset_dir(shot.id)
            dossier.mkdir(parents=True, exist_ok=True)
            resultat = generateur.image_pour(
                shot, channel, run.video_id, rupture=shot.asset_request.type == "stock"
            )
            assets.append(assets_images.copier_vers_run(
                resultat.chemin, run, shot.id, resultat.asset
            ))
            generees += int(resultat.genere)
            reutilisees += int(not resultat.genere)

            trace = vectoriser(
                resultat.chemin, dossier / "trace.svg", plafond=self.plafond_chemins
            )
            secondes_trace += trace.secondes
            traces[shot.id] = trace
            entree = {
                "shot": shot.id, "image": resultat.cle, "chemins": len(trace.contours),
                "plafond": self.plafond_chemins, "echelon": trace.echelon,
                "filter_speckle": trace.reglage["filter_speckle"],
                "essais": trace.essais, "secondes": round(trace.secondes, 3),
            }
            self.plafond_journal.append(entree)
            self.tracer(
                f"plafond de chemins {shot.id} : {len(trace.contours)}/{self.plafond_chemins} "
                f"contours après {trace.essais} passe(s) vtracer "
                f"(filter_speckle={trace.reglage['filter_speckle']}, "
                f"length_threshold={trace.reglage['length_threshold']}) en "
                f"{trace.secondes:.3f} s"
            )
        secondes_assets = time.perf_counter() - t_assets
        self.conn.close()
        self.conn = None

        maigres = [s for s, t in traces.items() if len(t.contours) < PLANCHER_CHEMINS]
        if maigres:
            self.tracer(
                f"ATTENTION : {len(maigres)} plan(s) sous {PLANCHER_CHEMINS} contours "
                f"({', '.join(maigres[:8])}) — dessin d'un seul tenant, tracé en un ou deux "
                f"gestes ; à surveiller si l'encre de l'image est elle aussi anormale"
            )

        spec = self.construire_specs(shotlist, channel, run, traces)

        t0 = time.perf_counter()
        manifestes = self.lancer_render(spec, run.video_id)
        durees = {shot.id: shot.duration_s for shot in shotlist.shots}
        temps_par_plan: dict[str, float] = {}
        t_decoupe = time.perf_counter()
        for manifeste in manifestes:
            temps_par_plan.update(self.decouper(manifeste, run, durees))
        secondes_decoupe = time.perf_counter() - t_decoupe
        secondes_total = time.perf_counter() - t0

        secondes_revideo = sum(float(m["secondes_rendu"]) for m in manifestes)
        images = sum(int(m["frames_utiles"]) for m in manifestes)
        secondes_video = sum(durees.values())
        comptes = [len(t.contours) for t in traces.values()] or [0]
        self.mesures.update({
            "assets_generated": generees,
            "assets_reused": reutilisees,
            "reuse_ratio": round(reutilisees / max(generees + reutilisees, 1), 3),
            "image_seconds": [round(s, 2) for s in generateur.temps_generation],
            "image_peak_mlx_gb": max(generateur.pics_mlx) if generateur.pics_mlx else None,
            "assets_seconds": round(secondes_assets, 2),
            "trace_seconds": round(secondes_trace, 3),
            "paths_median": sorted(comptes)[len(comptes) // 2],
            "paths_max": max(comptes),
            "paths_cap": self.plafond_chemins,
            "paths_resimplified": sum(1 for t in traces.values() if t.essais > 1),
            "revideo_seconds": round(secondes_revideo, 2),
            "decoupe_seconds": round(secondes_decoupe, 2),
            "render_seconds": round(secondes_total, 2),
            "frames": images,
            "revideo_fps": round(images / secondes_revideo, 1) if secondes_revideo else 0.0,
            "seconds_per_shot": round(
                (secondes_assets + secondes_total) / max(1, len(shotlist.shots)), 2
            ),
            "seconds_per_video_minute": round(
                (secondes_assets + secondes_total) / (secondes_video / 60), 1
            ) if secondes_video else 0.0,
            "realtime_ratio": round(
                (secondes_assets + secondes_total) / secondes_video, 3
            ) if secondes_video else 0.0,
            "resolution": self.resolution,
            "resolution_scale": self.echelle,
            "shot_seconds": {k: round(v, 3) for k, v in temps_par_plan.items()},
        })
        self.tracer(
            "mesures whiteboard : "
            + json.dumps({k: v for k, v in self.mesures.items()
                          if k not in ("shot_seconds", "image_seconds")}, ensure_ascii=False)
        )
        (run.racine / "whiteboard_chemins.json").write_text(
            json.dumps(self.plafond_journal, ensure_ascii=False, indent=1) + "\n",
            encoding="utf-8",
        )
        return assets

    # -- spécifications ------------------------------------------------------------------

    def construire_specs(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths,
        traces: dict[str, ResultatTrace],
    ) -> dict:
        """Écrit `render/specs/<video_id>/batch.json` pour la scène `draw_svg`, et la rend."""
        mots = (
            json.loads(run.words.read_text(encoding="utf-8")).get("words", [])
            if run.words.exists() else []
        )
        script = json.loads(run.script.read_text(encoding="utf-8")) if run.script.exists() else {}
        titres = {s["id"]: (s.get("on_screen_text") or "") for s in script.get("segments", [])}

        charte = channel.charte
        titre = self.police_titre(channel)
        manuscrite = self.police_manuscrite
        mains = self.mains()

        lots: list[dict] = []
        taille = max(1, self.taille_lot)
        for depart in range(0, len(shotlist.shots), taille):
            paquet = shotlist.shots[depart : depart + taille]
            lots.append({
                "name": f"lot_{depart // taille:03d}",
                "shots": [
                    {
                        "id": shot.id,
                        "scene": "draw_svg",
                        "duration_s": round(shot.duration_s, 3),
                        "props": self.props_du_plan(
                            shot, traces.get(shot.id), self._mots_du_plan(mots, shot),
                            titres.get(shot.segment_id, ""), depart + index,
                        ),
                    }
                    for index, shot in enumerate(paquet)
                ],
            })

        spec = {
            "video_id": run.video_id,
            "fps": video.FPS,
            "width": video.LARGEUR,
            "height": video.HAUTEUR,
            "resolution_scale": self.echelle,
            "workers": int(self.param("revideo.workers", 1) or 1),
            "out_dir": str(self.dossier_render / "out" / run.video_id),
            "charte": {
                # Le fond papier et l'encre viennent du **style** : une charte de chaîne décrit un
                # fond sombre, et un whiteboard sur fond sombre n'est plus un whiteboard. Les
                # couleurs de marqueur, elles, viennent bien de la charte — c'est par elles que
                # deux chaînes en whiteboard ne se ressemblent pas.
                "bg": str(self.param("draw.papier", "#f7f4ec") or "#f7f4ec"),
                "text": str(self.param("draw.encre", "#1a1a1a") or "#1a1a1a"),
                "text_outline": charte.palette.text_outline,
                "accent": charte.palette.accent,
                "highlight": charte.palette.highlight,
                "font_title": self.famille_css(titre),
                "font_body": self.famille_css(manuscrite),
                "marge_px": int(self.param("scene.marge_px", 110) or 110),
                "mains": mains,
                "grain": float(self.param("draw.grain", 0.05) or 0.05),
            },
            "lots": lots,
        }
        self.ecrire_specs(spec, run.video_id)
        return spec

    def props_du_plan(
        self, shot: Shot, trace: ResultatTrace | None, mots: list[dict],
        titre_segment: str, rang: int,
    ) -> dict:
        """Ce que la scène `draw-svg` reçoit pour un plan."""
        contours = trace.contours if trace else []
        longueurs = [round(_longueur(c), 1) for c in contours]
        return {
            "seed": shot.seed % 100000,
            "paths": contours,
            "lengths": longueurs,
            "fills": trace.groupes if trace else [],
            "bbox": trace.boite if trace else [0, 0, video.LARGEUR, video.HAUTEUR],
            "svg_width": trace.largeur if trace else video.LARGEUR,
            "svg_height": trace.hauteur if trace else video.HAUTEUR,
            "draw_ratio": self.part_trace,
            # Deux plans voisins ne tiennent pas le feutre de la même façon : sans cette
            # alternance, vingt plans d'affilée montrent exactement la même main au même angle.
            "hand": rang % 2,
            "words": mots,
            "on_screen_text": shot.on_screen_text or "",
            "title": titre_segment if titre_segment != (shot.on_screen_text or "") else "",
            "marker": rang % 3,
            "shake": bool(self.param("draw.tremblement", True)),
            "is_sponsor": shot.is_sponsor,
            "disclosure": self.texte_divulgation if shot.is_sponsor else None,
        }

    # -- contrat StyleEngine -------------------------------------------------------------

    def render_shot(
        self, shot: Shot, assets: list[Asset], channel: Channel, run: RunPaths
    ) -> Path:
        """Rend `clips/<shot>.mp4`. Le lot l'a normalement déjà produit ; sinon, il est rejoué seul."""
        sortie = run.clip(shot.id)
        if sortie.exists() and not self.verify_clip(sortie, shot.duration_s):
            return sortie
        fichier = self.dossier_render / "specs" / run.video_id / "batch.json"
        if not fichier.exists():
            raise RenduRevideoEchoue(
                f"{shot.id} : spécification absente ({fichier}) — `prepare_assets` n'a pas tourné"
            )
        spec = json.loads(fichier.read_text(encoding="utf-8"))
        lot = next(
            (l["name"] for l in spec["lots"] if any(p["id"] == shot.id for p in l["shots"])),
            None,
        )
        if lot is None:
            raise RenduRevideoEchoue(f"{shot.id} : absent de {fichier}")
        manifestes = self.lancer_render(spec, run.video_id, lot=lot)
        self.decouper(manifestes[0], run, {shot.id: shot.duration_s})
        return sortie


__all__ = [
    "WhiteboardEngine", "DessinIndisponible", "PLAFOND_CHEMINS", "PROMPT_STYLE",
    "prompt_whiteboard", "vectoriser", "ordonner", "ResultatTrace",
]
