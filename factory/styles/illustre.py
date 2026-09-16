"""Moteur « illustré animé » — une image générée par plan, mise en mouvement, et du texte dessus.

C'est le style des chaînes qui performent au registre, et le premier rendu présentable du
système. Un plan = quatre couches, dans cet ordre :

1. **Mouvement** — parallaxe 2.5D (trois couches issues d'une carte de profondeur) ou Ken Burns.
   Le repli n'est pas un aveu : les deux sont notés 4/5 à l'étape 5.2. Ken Burns sert quand la
   profondeur échoue, quand le plan est trop court pour qu'un glissement se lise, ou quand la
   configuration le demande.
2. **Vignettage** — léger, pour ramener l'œil au centre et asseoir le texte sur un bord assombri.
3. **Texte à l'écran** — rastérisé par Pillow (`drawtext` est absent de ce build ffmpeg, mesuré à
   l'étape 12.1), composé par `overlay` avec une apparition par alpha.
4. **Bandeau de divulgation** — sur toute la durée du plan `is_sponsor`, sans rampe : la loi
   française 2023-451 l'exige **pendant** la promotion (`CONFORMITE.md` § 3).

**Ce que ce moteur ne fait pas, et pourquoi.** Le découpage demande un asset `stock` sur les plans
de rupture (`shotlist.TYPES_PAR_MOTEUR`), mais les banques libres sont livrées par l'**étape 17**.
En attendant, un plan `stock` reçoit une image générée avec la mention de rupture dans son prompt
— cadre large, fond différent — et le journal le signale à chaque passage. Le plan est servi, la
règle « la rupture change de type d'asset » ne l'est pas : c'est écrit plutôt que masqué.

**L'ordre des modèles n'est pas négociable.** `prepare_assets` génère d'abord toutes les images
(un sous-processus mflux par image, qui se termine), **puis** lance un unique sous-processus de
profondeur sur le lot. Jamais les deux ensemble (`ARCHITECTURE` § 1.3) ; et le lot paie le
chargement du modèle de profondeur une fois par run au lieu d'une fois par plan.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from factory import video
from factory.assets import images as assets_images
from factory.assets import parallax
from factory.core import db
from factory.core.models import Asset, Channel, Shot, Shotlist
from factory.core.paths import RunPaths
from factory.styles.base import MoteurBase

#: Marge de sécurité du texte à l'écran, en pixels.
MARGE_PX = 96
#: Taille du texte à l'écran. Plus grande que dans `cartes` : il se lit sur une image, pas sur un
#: aplat de charte, et doit gagner contre le détail.
TAILLE_TITRE_PX = 82
TAILLE_CORPS_PX = 52
#: Un texte à l'écran tient en trois lignes ou il n'est pas un texte à l'écran.
LIGNES_MAX = 3
#: Durée de l'apparition du texte, en secondes.
APPARITION_S = 0.45
#: Opacité du cartouche posé derrière le texte : sans lui, un titre clair sur une image claire
#: n'est pas lisible, et la lisibilité est un critère noté de cette étape.
OPACITE_CARTOUCHE = 0.72
#: Vignettage : angle du filtre ffmpeg. Plus l'angle est petit, plus le coin est sombre.
VIGNETTE_ANGLE = "PI/5"
#: Licence d'un fond de charte (plans `card` et repli) : charte + police OFL, aucun pixel généré.
LICENCE_CARTE = "OFL-1.1"
LICENCE_CARTE_URL = "https://openfontlicense.org/open-font-license-official-text/"


@dataclass
class IllustreEngine(MoteurBase):
    """Moteur de style « illustré animé » (`STYLE_ENGINES["illustre_anime"]`)."""

    name: str = "illustre"
    backend: str = "ffmpeg"
    #: Ouverte à `prepare_assets`, fermée à la fin : la bibliothèque est un index, pas un cache
    #: en mémoire. `None` tant que `prepare_assets` n'a pas tourné.
    conn: sqlite3.Connection | None = None
    #: Mesures du run, relues par l'étape `render` pour le manifeste.
    mesures: dict[str, object] = field(default_factory=dict)

    # -- paramètres ----------------------------------------------------------------------

    @property
    def resolution(self) -> str:
        return str(self.param("image.resolution", assets_images.RESOLUTION_DEFAUT))

    @property
    def modele_image(self) -> str:
        return str(self.param("image.model", assets_images.MODELE_DEFAUT))

    @property
    def etapes(self) -> int:
        return int(self.param("image.steps", assets_images.ETAPES_DEFAUT) or 4)

    @property
    def modele_profondeur(self) -> str:
        return str(self.param("depth.model", parallax.MODELE_DEFAUT))

    @property
    def mouvement_defaut(self) -> str:
        return str(self.param("motion.default", "parallax"))

    @property
    def surechantillonnage(self) -> int:
        return int(self.param("motion.ken_burns_supersample", 4) or 4)

    @property
    def couches_parallaxe(self) -> int:
        return int(self.param("motion.parallax_layers", 3) or 3)

    @property
    def controle_trous(self) -> bool:
        return bool(self.param("motion.magenta_hole_check", False))

    def dossier_profondeur(self) -> Path:
        dossier = assets_images.dossier_bibliotheque(self.racine).parent / "depth"
        dossier.mkdir(parents=True, exist_ok=True)
        return dossier

    # -- prepare_assets ------------------------------------------------------------------

    def prepare_assets(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths
    ) -> list[Asset]:
        """Une image par plan (générée ou reprise), les calques de texte, les cartes de profondeur."""
        video_id = run.video_id
        self.conn = db.ouvrir(self.racine / "workspace" / "factory.db")
        generateur = assets_images.GenerateurImages(
            conn=self.conn, style_id=self.style.id, racine=self.racine, journal=self.journal,
            modele=self.modele_image, resolution=self.resolution, etapes=self.etapes,
        )
        # **Le LLM d'abord, seul, puis mflux, seul, puis la profondeur, seule.** Trois modèles
        # dans un run, jamais deux à la fois : chaque appel est un sous-processus qui se termine
        # avant que le suivant commence (`ARCHITECTURE` § 1.3).
        a_traduire = [
            s.asset_request.prompt_or_keywords for s in shotlist.shots
            if s.asset_request.type != "card"
        ]
        generateur.traductions = assets_images.traduire_intentions(
            a_traduire, channel.lang, racine=self.racine, journal=self.journal
        )

        police_titre = self.police_titre(channel)
        police_corps = self.police_corps(channel)

        assets: list[Asset] = []
        reutilisees = generees = 0
        stock_replies = 0
        #: image de bibliothèque → destination de sa carte de profondeur, nommée par `asset_id`.
        #: C'est `asset_id` qui joint l'image du run et celle de la bibliothèque : les deux
        #: fichiers ont le même contenu et jamais le même nom.
        a_animer: dict[Path, Path] = {}
        for shot in shotlist.shots:
            dossier = run.asset_dir(shot.id)
            dossier.mkdir(parents=True, exist_ok=True)
            if shot.asset_request.type == "card":
                assets.append(self._fond_de_charte(shot, channel, run))
                continue
            rupture = shot.asset_request.type == "stock"
            if rupture:
                stock_replies += 1
            resultat = generateur.image_pour(shot, channel, video_id, rupture=rupture)
            assets.append(assets_images.copier_vers_run(
                resultat.chemin, run, shot.id, resultat.asset
            ))
            if self._veut_parallaxe(shot):
                a_animer[resultat.chemin] = (
                    self.dossier_profondeur() / f"{resultat.asset.asset_id}.png"
                )
            if resultat.genere:
                generees += 1
            else:
                reutilisees += 1

        if stock_replies:
            self.tracer(
                f"ATTENTION : {stock_replies} plan(s) de rupture demandent un asset `stock` "
                "(banques libres, étape 17) et reçoivent une image générée en cadre large — "
                "la rupture change de cadre et de fond, pas de type d'asset"
            )

        # Les calques de texte sont rastérisés ici, une fois : `render_shot` ne fait que composer.
        for shot in shotlist.shots:
            if shot.on_screen_text or shot.is_sponsor:
                calque = run.asset_dir(shot.id) / "overlay.png"
                if not calque.exists():
                    self._composer_texte(shot, channel, police_titre, police_corps).save(
                        calque, "PNG"
                    )

        # Profondeur : après toutes les images, jamais pendant. Les plans trop courts pour une
        # parallaxe n'ont pas de carte à calculer — c'est autant de modèle qu'on ne charge pas.
        profondeur = parallax.ResultatProfondeur()
        if a_animer:
            profondeur = parallax.cartes_profondeur(
                sorted(a_animer.items()), racine=self.racine,
                modele=self.modele_profondeur, journal=self.journal,
            )

        self.mesures = {
            "assets_generated": generees,
            "assets_reused": reutilisees,
            "reuse_ratio": round(reutilisees / max(generees + reutilisees, 1), 3),
            "image_seconds": [round(s, 2) for s in generateur.temps_generation],
            "image_peak_mlx_gb": max(generateur.pics_mlx) if generateur.pics_mlx else None,
            "depth_maps": len(profondeur.cartes),
            "depth_failures": len(profondeur.echecs),
            "depth_seconds": round(profondeur.secondes, 2),
            "stock_fallback_shots": stock_replies,
            "resolution": self.resolution,
        }
        self.tracer(
            f"prepare_assets : {generees} générée(s), {reutilisees} reprise(s) de bibliothèque, "
            f"{len(profondeur.cartes)} carte(s) de profondeur"
        )
        self.conn.close()
        self.conn = None
        return assets

    def _veut_parallaxe(self, shot: Shot) -> bool:
        """Un plan trop court ne montre pas un glissement de couches : Ken Burns s'y lit mieux."""
        return (
            self.mouvement_defaut == "parallax"
            and shot.duration_s >= parallax.DUREE_MINIMALE_PARALLAXE_S
        )

    def _fond_de_charte(self, shot: Shot, channel: Channel, run: RunPaths) -> Asset:
        """Plan `card` : un fond de charte, comme dans `cartes.py`. Aucun pixel généré."""
        dossier = run.asset_dir(shot.id)
        fichier = dossier / "image.png"
        if not fichier.exists():
            palette = channel.charte.palette
            fond = Image.new("RGB", (video.LARGEUR, video.HAUTEUR), palette.bg)
            bande = video.rectangle_arrondi(
                (video.LARGEUR, 10), 0, palette.accent, 1.0
            )
            video.coller(fond.convert("RGBA"), bande, (0, video.HAUTEUR - 10))
            fond.save(fichier, "PNG")
        asset = Asset(
            asset_id=self.identifiant_asset(fichier),
            path=f"assets/{shot.id}/image.png",
            provider="charte",
            source_url=f"config/channels/{channel.id}.yaml#charte@{channel.charte.version}",
            author=f"BMS ({channel.name})",
            licence=LICENCE_CARTE,
            licence_url=LICENCE_CARTE_URL,
            attribution_line=None,
            downloaded_at=self.maintenant(),
            person_release=None,
            generator=None,
            realistic=False,
            has_text=bool(shot.on_screen_text) or shot.is_sponsor,
            c2pa_present=False,
        )
        run.licence(shot.id).write_text(
            json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return asset

    def _composer_texte(
        self, shot: Shot, channel: Channel, police_titre: video.Police,
        police_corps: video.Police,
    ) -> Image.Image:
        """Calque RGBA : cartouche, texte à l'écran, souligné d'accent, bandeau de divulgation."""
        palette = channel.charte.palette
        calque = Image.new("RGBA", (video.LARGEUR, video.HAUTEUR), (0, 0, 0, 0))
        texte = (shot.on_screen_text or "").strip()
        if texte:
            bloc = video.rasteriser_texte(
                texte, police_titre, TAILLE_TITRE_PX, palette.text,
                largeur_max=video.LARGEUR - 2 * MARGE_PX, lignes_max=LIGNES_MAX,
                contour=palette.text_outline, contour_px=4,
            )
            # Le cartouche est la parade mesurée à la lisibilité : un titre blanc sur une image
            # générée claire disparaît, et le contour seul ne suffit pas sur du détail.
            cartouche = video.rectangle_arrondi(
                (bloc.width + 2 * MARGE_PX // 2, bloc.height + MARGE_PX // 2), 24,
                palette.bg, OPACITE_CARTOUCHE,
            )
            x = (video.LARGEUR - cartouche.width) // 2
            y = video.HAUTEUR - MARGE_PX - cartouche.height
            video.coller(calque, cartouche, (x, y))
            video.coller(calque, bloc, (x + MARGE_PX // 2, y + MARGE_PX // 4))
            largeur_souligne = max(80, round(bloc.width * 0.35))
            video.coller(
                calque,
                video.rectangle_arrondi((largeur_souligne, 8), 4, palette.highlight, 1.0),
                (x + (cartouche.width - largeur_souligne) // 2, y + cartouche.height - 18),
            )
        if shot.is_sponsor:
            video.coller(calque, self._bandeau_divulgation(channel, police_corps),
                         (MARGE_PX, MARGE_PX))
        return calque

    def _bandeau_divulgation(self, channel: Channel, police: video.Police) -> Image.Image:
        """Bandeau « Publicité ». Le texte vient de `config/languages/<code>.yaml`, jamais du code."""
        texte = self.texte_divulgation or "Publicité"
        palette = channel.charte.palette
        bloc = video.rasteriser_texte(
            texte.upper(), police, round(TAILLE_CORPS_PX * 0.62), palette.bg,
            largeur_max=round(video.LARGEUR * 0.4), lignes_max=1,
        )
        interne = 28
        fond = video.rectangle_arrondi(
            (bloc.width + 2 * interne, bloc.height + interne), 12, palette.highlight, 1.0
        )
        video.coller(fond, bloc, (interne, interne // 2))
        return fond

    # -- render_shot ---------------------------------------------------------------------

    def render_shot(
        self, shot: Shot, assets: list[Asset], channel: Channel, run: RunPaths
    ) -> Path:
        """Rend `clips/shot_XX.mp4` : mouvement + vignettage + texte, à la durée exacte du plan."""
        run.clips_dir.mkdir(parents=True, exist_ok=True)
        sortie = run.clip(shot.id)
        image = run.asset_dir(shot.id) / "image.png"
        if not image.exists():
            raise FileNotFoundError(
                f"{shot.id} : image absente ({image}) — `prepare_assets` n'a pas été appelée"
            )
        calque = run.asset_dir(shot.id) / "overlay.png"
        duree = shot.duration_s

        carte = self._carte_de(assets)
        if carte is not None and self._veut_parallaxe(shot):
            return self._rendre_parallaxe(shot, image, carte, calque, sortie, duree)
        if self.mouvement_defaut == "parallax" and self._veut_parallaxe(shot):
            self.tracer(f"{shot.id} : profondeur absente — repli Ken Burns")
        return self._rendre_ken_burns(shot, image, calque, sortie, duree)

    def _carte_de(self, assets: list[Asset]) -> Path | None:
        """Carte de profondeur du plan, cherchée par `asset_id` — le seul lien stable.

        L'image du run est une copie de celle de la bibliothèque : même contenu, jamais le même
        nom. `asset_id` est `sha256(fichier)[:16]`, donc identique pour les deux.
        """
        for asset in assets:
            carte = self.dossier_profondeur() / f"{asset.asset_id}.png"
            if carte.exists() and carte.stat().st_size > 0:
                return carte
        return None

    def _rendre_parallaxe(
        self, shot: Shot, image: Path, carte: Path, calque: Path, sortie: Path, duree: float
    ) -> Path:
        """Parallaxe 2.5D : les couches sont découpées ici et jetées ensuite.

        Trois PNG RGBA 1080p pèsent ~12 Mo par plan : les garder coûterait 1,5 Go pour ce run
        seul, pour 0,7 s de découpe économisée. Le disque est la ressource rare, pas la seconde.
        """
        with tempfile.TemporaryDirectory(prefix=f"parallax_{shot.id}_") as temporaire:
            dossier = Path(temporaire)
            couches = parallax.couches(
                image, carte, dossier, nombre=self.couches_parallaxe
            )
            if self.controle_trous:
                trous = parallax.trous_magenta(
                    couches, duree, shot.motion, shot.seed, dossier / "temoin.png"
                )
                if trous > 0:
                    self.tracer(f"{shot.id} : {trous} pixel(s) de trou en parallaxe")
            apres = f"vignette=angle={VIGNETTE_ANGLE}"
            if not calque.exists():
                filtre = parallax.chaine_parallaxe(
                    couches, duree, shot.motion, shot.seed,
                    apres=f"{apres},format=yuv420p", etiquette="v",
                )
                entrees = self._entrees_couches(couches, duree)
            else:
                filtre = parallax.chaine_parallaxe(
                    couches, duree, shot.motion, shot.seed, apres=apres, etiquette="base"
                )
                indice = 1 + len(couches)
                filtre += (
                    f";[{indice}:v]{video.filtre_apparition(APPARITION_S)}[txt];"
                    f"[base][txt]overlay=0:0:format=auto,format=yuv420p[v]"
                )
                entrees = self._entrees_couches(couches, duree) + [
                    "-loop", "1", "-framerate", str(video.FPS), "-t", f"{duree:.3f}",
                    "-i", str(calque),
                ]
            arguments = entrees + ["-filter_complex", filtre, "-map", "[v]"]
            arguments += video.arguments_encodage(sortie, duree)
            self.encoder(arguments)
        return sortie

    def _entrees_couches(self, couches: list[Path], duree: float) -> list[str]:
        """Entrée 0 : le fond noir qui fixe la taille et la cadence. Puis une entrée par couche."""
        entrees = [
            "-f", "lavfi",
            "-i", f"color=c=black:s={video.LARGEUR}x{video.HAUTEUR}:r={video.FPS}:d={duree:.3f}",
        ]
        for couche in couches:
            entrees += ["-loop", "1", "-t", f"{duree:.3f}", "-i", str(couche)]
        return entrees

    def _rendre_ken_burns(
        self, shot: Shot, image: Path, calque: Path, sortie: Path, duree: float
    ) -> Path:
        """Repli Ken Burns : `zoompan` suréchantillonné ×4, vignettage, puis le texte."""
        images_n = max(1, round(duree * video.FPS))
        grande_l = video.LARGEUR * self.surechantillonnage
        grande_h = video.HAUTEUR * self.surechantillonnage
        depart, arrivee = 1.0, 1.08
        if shot.motion == "zoom_out" or (shot.motion == "static" and shot.seed % 2):
            depart, arrivee = arrivee, depart
        pas = abs(arrivee - depart) / images_n
        zoom = (
            f"min(zoom+{pas:.6f},{arrivee:.3f})" if arrivee > depart
            else f"max({depart:.3f}-on*{pas:.6f},{arrivee:.3f})"
        )
        course = 0.03 * video.LARGEUR * (1 if shot.seed % 2 == 0 else -1)
        if shot.motion == "pan":
            course *= 2
        mouvement = (
            f"scale={grande_l}:{grande_h}:flags=bicubic,"
            f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)+{course:.1f}*on/{images_n}':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={video.LARGEUR}x{video.HAUTEUR}:fps={video.FPS},"
            f"vignette=angle={VIGNETTE_ANGLE}"
        )
        if not calque.exists():
            arguments = ["-i", str(image), "-vf", f"{mouvement},format=yuv420p"]
        else:
            filtre = (
                f"[0:v]{mouvement}[base];"
                f"[1:v]{video.filtre_apparition(APPARITION_S)}[txt];"
                f"[base][txt]overlay=0:0:format=auto,format=yuv420p[v]"
            )
            arguments = [
                "-i", str(image),
                "-loop", "1", "-framerate", str(video.FPS), "-t", f"{duree:.3f}", "-i", str(calque),
                "-filter_complex", filtre, "-map", "[v]",
            ]
        arguments += video.arguments_encodage(sortie, duree)
        self.encoder(arguments)
        return sortie

    # -- divers --------------------------------------------------------------------------

    @staticmethod
    def taille_bibliotheque(racine: Path) -> tuple[int, float]:
        """Nombre de fichiers et poids en mégaoctets de `workspace/library/images/`."""
        dossier = racine / "workspace" / "library" / "images"
        if not dossier.exists():
            return 0, 0.0
        fichiers = [f for f in dossier.rglob("*") if f.is_file()]
        return len(fichiers), round(sum(f.stat().st_size for f in fichiers) / 1e6, 2)
