"""Moteur « documentaire » — du réel, monté : clips de banques libres, bandeau bas, étalonnage.

Le pari de ce style est l'inverse de celui du moteur illustré. Là-bas, un modèle fabrique une
image que personne n'a jamais vue ; ici, on va chercher une image que quelqu'un a filmée, et tout
le travail est de la **choisir**, de la **couper au bon endroit** et de l'**unifier**. C'est un
travail de monteur, pas de générateur : aucun modèle d'image n'est chargé tant qu'une banque
répond (`ARCHITECTURE` § 1.3 y gagne autant que le temps de rendu).

Un plan = quatre couches, dans cet ordre :

1. **La source** — un clip de banque coupé à la durée du plan, ou une image fixe mise en
   mouvement. Le point de coupe n'est pas le début du fichier par défaut : c'est la fenêtre la
   plus mouvementée, estimée par différence d'images (`tblend=difference`, la mesure même dont le
   banc se sert pour juger le mouvement). Les trois premières secondes d'un clip de banque sont
   très souvent son plan le plus mort.
2. **Le cadre** — mise à l'échelle par le grand côté puis recadrage 1920×1080, jamais une
   déformation ; et un léger ralenti ou accéléré (± 8 %) pour que la fenêtre choisie tombe
   exactement sur la durée du plan.
3. **L'étalonnage** — discret, par LUT `.cube` si la charte en fournit une, sinon par
   `colorbalance` + `eq`. **C'est lui qui fait tenir la vidéo ensemble** : quinze fournisseurs,
   quinze balances des blancs ; sans étalonnage commun on voit le collage.
4. **Le texte** — bandeau bas (*lower third*) rastérisé par Pillow, et le bandeau « Publicité »
   sur toute la durée d'un plan sponsorisé (`CONFORMITE.md` § 3).

**Le mouvement des images fixes est calculé dans le bon repère, et c'est une correction.**
`illustre.py` exprime la course du panoramique en pixels de l'image finale (1920) puis l'applique
dans le repère de `zoompan`, qui travaille sur l'image suréchantillonnée ×4 : le déplacement vaut
le quart de ce qu'il paraît, ≈ 7,5 px/s, invisible (`STATE.md`, étape 16). Ici la course est
multipliée par le suréchantillonnage, et le zoom progresse sur `on` — un compteur d'images — au
lieu de s'accumuler sur `zoom`, qui ne s'accumule pas à `d=1` sur une source `-loop 1`. Le rendu
du moteur illustré n'est pas touché : Thomas l'a explicitement voulu tel quel.

**Un plan n'échoue jamais.** Banques → image générée + Ken Burns → fond de charte. Chaque degré
est compté au manifeste : un repli silencieux serait un mensonge sur la nature de la vidéo.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from factory import video
from factory.assets import images as assets_images
from factory.assets import stock
from factory.core import db
from factory.core.models import Asset, Channel, Shot, Shotlist
from factory.core.paths import RunPaths
from factory.styles.base import MoteurBase

#: Marge de sécurité du texte à l'écran, en pixels.
MARGE_PX = 96
#: Bandeau bas : hauteur de la bande d'accent, taille du texte, opacité du fond.
ACCENT_PX = 10
TAILLE_BANDEAU_PX = 58
TAILLE_CORPS_PX = 52
LIGNES_MAX = 2
OPACITE_BANDEAU = 0.82
#: Le bandeau bas se pose **au-dessus** de la zone des sous-titres, jamais dedans : la charte
#: réserve `subtitles.margin_v_px` plus deux lignes de `subtitles.size_px`.
GARDE_SOUS_TITRES_PX = 60
#: Durée de l'apparition du texte, en secondes.
APPARITION_S = 0.45
#: Vitesses de lecture employées en rotation ; ± 8 % est ce qui s'ajuste sans s'entendre.
ALTERNANCE_VITESSE: tuple[float, ...] = (1.0, 0.92, 1.08, 0.96)
#: Analyse de mouvement : images examinées par seconde. 2 suffit à situer une fenêtre.
ANALYSE_IPS = 2
#: En deçà de cette marge, la source n'offre aucun choix de fenêtre : on part du début.
MARGE_ANALYSE_S = 2.0
#: Licence d'un fond de charte (dernier repli) : charte + police OFL, aucun pixel généré.
LICENCE_CARTE = "OFL-1.1"
LICENCE_CARTE_URL = "https://openfontlicense.org/open-font-license-official-text/"


@dataclass
class DocumentaireEngine(MoteurBase):
    """Moteur de style « documentaire » (`STYLE_ENGINES["documentaire"]`)."""

    name: str = "documentaire"
    backend: str = "ffmpeg"
    #: Ouverte à `prepare_assets`, fermée à la fin.
    conn: sqlite3.Connection | None = None
    #: Mesures du run, relues par l'étape `render` pour le manifeste.
    mesures: dict[str, object] = field(default_factory=dict)
    #: `shot_id` → nature de l'asset servi : `video`, `image_stock`, `image_generee`, `carte`.
    natures: dict[str, str] = field(default_factory=dict)
    #: Profil de mouvement déjà mesuré, par fichier : un clip réemployé n'est pas réanalysé.
    _profils: dict[str, list[tuple[float, float]]] = field(default_factory=dict)

    # -- paramètres ----------------------------------------------------------------------

    @property
    def chaine_fournisseurs(self) -> tuple[str, ...]:
        declares = self.param("stock.providers", None)
        if not isinstance(declares, list) or not declares:
            return stock.CHAINE_DEFAUT
        # Le YAML peut nommer un fournisseur que ce module ne sait pas interroger : il est
        # écarté ici plutôt que de produire une requête vide à chaque plan.
        return tuple(p for p in declares if p in stock.CHAINE_DEFAUT) or stock.CHAINE_DEFAUT

    @property
    def surechantillonnage(self) -> int:
        return int(self.param("motion.ken_burns_supersample", 4) or 4)

    @property
    def course_ratio(self) -> float:
        return float(self.param("motion.course_ratio", 0.06) or 0.06)

    @property
    def zoom_arrivee(self) -> float:
        return float(self.param("motion.zoom", 1.10) or 1.10)

    @property
    def resolution_repli(self) -> str:
        return str(self.param("image.resolution", assets_images.RESOLUTION_DEFAUT))

    @property
    def modele_repli(self) -> str:
        return str(self.param("image.model", assets_images.MODELE_DEFAUT))

    def etalonnage(self) -> str:
        """Chaîne de filtres d'étalonnage, LUT si la charte en fournit une, sinon `colorbalance`.

        Une LUT `.cube` libre (domaine public ou CC-BY) déposée dans `config/luts/` prime ; sans
        elle, un rééquilibrage discret suffit à ce qu'on cherche — rapprocher des sources de
        températures différentes, pas « faire un look ».
        """
        fichier = self.param("grade.lut", None)
        if fichier:
            chemin = self.racine / str(fichier)
            if chemin.exists():
                echappe = str(chemin).replace("\\", "\\\\").replace(":", "\\:")
                return f"lut3d=file='{echappe}'"
            self.tracer(f"étalonnage : LUT {fichier} absente — repli colorbalance")
        rouge = float(self.param("grade.rouge", -0.015) or 0.0)
        vert = float(self.param("grade.vert", 0.0) or 0.0)
        bleu = float(self.param("grade.bleu", 0.030) or 0.0)
        contraste = float(self.param("grade.contraste", 1.05) or 1.0)
        saturation = float(self.param("grade.saturation", 0.94) or 1.0)
        return (
            f"colorbalance=rs={rouge:.3f}:gs={vert:.3f}:bs={bleu:.3f},"
            f"eq=contrast={contraste:.3f}:saturation={saturation:.3f}"
        )

    # -- prepare_assets ------------------------------------------------------------------

    def prepare_assets(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths
    ) -> list[Asset]:
        """Un asset réel par plan, puis les replis générés, puis les calques de texte.

        **L'ordre est celui de la règle « un seul modèle résident »** : le LLM des mots-clés
        d'abord (un sous-processus qui se termine), les banques ensuite (aucun modèle), mflux en
        dernier et seulement pour les plans que les banques n'ont pas servis.
        """
        video_id = run.video_id
        self.conn = db.ouvrir(self.racine / "workspace" / "factory.db")
        banque = stock.BanqueStock(
            conn=self.conn, racine=self.racine, journal=self.journal,
            chaine=self.chaine_fournisseurs,
        )
        self.tracer(
            "stock : fournisseurs interrogeables — "
            + (", ".join(banque.fournisseurs_actifs()) or "aucun (clés absentes)")
        )

        intentions = [
            s.asset_request.prompt_or_keywords for s in shotlist.shots
            if s.asset_request.type == "stock"
        ]
        banque.requetes = stock.requetes_pour(
            intentions, racine=self.racine, journal=self.journal
        )
        try:  # réemploi sémantique (étape 29) : accélérateur, jamais une dépendance
            from factory import library

            banque.semantique = library.IndexSemantique.charger(self.conn, "stock")
            banque.semantique.preparer(intentions, racine=self.racine)
        except Exception as erreur:
            banque.semantique = None
            self.tracer(f"réemploi sémantique désactivé : {erreur}")

        assets: dict[str, Asset] = {}
        a_generer: list[Shot] = []
        for shot in shotlist.shots:
            run.asset_dir(shot.id).mkdir(parents=True, exist_ok=True)
            if shot.asset_request.type != "stock":
                a_generer.append(shot)
                continue
            resultat = banque.asset_pour(shot, channel, video_id)
            if resultat is None:
                a_generer.append(shot)
                continue
            assets[shot.id] = self._deposer(resultat.chemin, run, shot.id, resultat.asset)
            self.natures[shot.id] = "video" if resultat.est_video else "image_stock"

        generees = self._generer_replis(a_generer, channel, run, video_id, assets)

        police_titre = self.police_titre(channel)
        police_corps = self.police_corps(channel)
        for shot in shotlist.shots:
            if shot.on_screen_text or shot.is_sponsor:
                calque = run.asset_dir(shot.id) / "overlay.png"
                if not calque.exists():
                    self._composer_texte(shot, channel, police_titre, police_corps).save(
                        calque, "PNG"
                    )

        natures = list(self.natures.values())
        self.mesures = {
            **banque.mesures(),
            "stock_generees": generees,
            "shots_video": natures.count("video"),
            "shots_image_stock": natures.count("image_stock"),
            "shots_image_generee": natures.count("image_generee"),
            "shots_carte": natures.count("carte"),
            "assets_generated": generees,
            "assets_reused": len(shotlist.shots) - generees,
            "reuse_ratio": round(
                (len(shotlist.shots) - generees) / max(len(shotlist.shots), 1), 3
            ),
            "stock_library_mb": stock.taille_bibliotheque(self.racine)[1],
        }
        self.tracer(
            f"prepare_assets : {natures.count('video')} clip(s) vidéo, "
            f"{natures.count('image_stock')} image(s) de banque, {generees} générée(s), "
            f"{natures.count('carte')} fond(s) de charte"
        )
        self.conn.close()
        self.conn = None
        return [assets[s.id] for s in shotlist.shots if s.id in assets]

    def _generer_replis(
        self, shots: list[Shot], channel: Channel, run: RunPaths, video_id: str,
        assets: dict[str, Asset],
    ) -> int:
        """Images générées pour les plans que les banques n'ont pas servis. mflux, en dernier."""
        if not shots:
            return 0
        assert self.conn is not None
        generateur = assets_images.GenerateurImages(
            conn=self.conn, style_id=self.style.id, racine=self.racine, journal=self.journal,
            modele=self.modele_repli, resolution=self.resolution_repli,
            etapes=int(self.param("image.steps", assets_images.ETAPES_DEFAUT) or 4),
        )
        generateur.traductions = assets_images.traduire_intentions(
            [s.asset_request.prompt_or_keywords for s in shots], channel.lang,
            racine=self.racine, journal=self.journal,
        )
        generees = 0
        for shot in shots:
            try:
                resultat = generateur.image_pour(shot, channel, video_id, rupture=False)
            except assets_images.ImageIndisponible as erreur:
                self.tracer(f"{shot.id} : génération impossible ({erreur}) — fond de charte")
                assets[shot.id] = self._fond_de_charte(shot, channel, run)
                self.natures[shot.id] = "carte"
                continue
            except assets_images.CharteIncomplete as erreur:
                self.tracer(f"{shot.id} : charte sans style d'image ({erreur}) — fond de charte")
                assets[shot.id] = self._fond_de_charte(shot, channel, run)
                self.natures[shot.id] = "carte"
                continue
            assets[shot.id] = assets_images.copier_vers_run(
                resultat.chemin, run, shot.id, resultat.asset
            )
            self.natures[shot.id] = "image_generee"
            if resultat.genere:
                generees += 1
        return generees

    def _deposer(self, source: Path, run: RunPaths, shot_id: str, asset: Asset) -> Asset:
        """Pose l'asset de bibliothèque dans `assets/<shot>/` et y écrit sa licence.

        **Un lien matériel, pas une copie** : 130 clips de banque recopiés pèsent plusieurs
        gigaoctets pour un run, et le disque est la ressource rare de cette machine
        (`CLAUDE.md` § 3). Le lien rend le run lisible seul et ne coûte pas un octet. Sur un
        système de fichiers qui le refuse, on retombe sur la copie plutôt que sur l'échec.
        """
        dossier = run.asset_dir(shot_id)
        dossier.mkdir(parents=True, exist_ok=True)
        destination = dossier / f"source{source.suffix}"
        if not destination.exists():
            try:
                os.link(source, destination)
            except OSError:
                shutil.copy2(source, destination)
        dans_le_run = asset.model_copy(
            update={"path": f"assets/{shot_id}/{destination.name}"}
        )
        run.licence(shot_id).write_text(
            json.dumps(dans_le_run.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return dans_le_run

    def _fond_de_charte(self, shot: Shot, channel: Channel, run: RunPaths) -> Asset:
        """Dernier repli : un fond de charte. Aucun pixel généré, aucun octet téléchargé."""
        dossier = run.asset_dir(shot.id)
        fichier = dossier / "source.png"
        if not fichier.exists():
            palette = channel.charte.palette
            fond = Image.new("RGB", (video.LARGEUR, video.HAUTEUR), palette.bg)
            bande = video.rectangle_arrondi((video.LARGEUR, ACCENT_PX), 0, palette.accent, 1.0)
            video.coller(fond.convert("RGBA"), bande, (0, video.HAUTEUR - ACCENT_PX))
            fond.save(fichier, "PNG")
        asset = Asset(
            asset_id=self.identifiant_asset(fichier),
            path=f"assets/{shot.id}/source.png",
            provider="charte",
            source_url=f"config/channels/{channel.id}.yaml#charte@{channel.charte.version}",
            author=f"BMS ({channel.name})",
            licence=LICENCE_CARTE, licence_url=LICENCE_CARTE_URL, attribution_line=None,
            downloaded_at=self.maintenant(), person_release=None, generator=None,
            realistic=False, has_text=bool(shot.on_screen_text) or shot.is_sponsor,
            c2pa_present=False,
        )
        run.licence(shot.id).write_text(
            json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return asset

    # -- texte ---------------------------------------------------------------------------

    def _composer_texte(
        self, shot: Shot, channel: Channel, police_titre: video.Police,
        police_corps: video.Police,
    ) -> Image.Image:
        """Calque RGBA : bandeau bas aligné à gauche, et bandeau de divulgation si sponsor."""
        palette = channel.charte.palette
        calque = Image.new("RGBA", (video.LARGEUR, video.HAUTEUR), (0, 0, 0, 0))
        texte = (shot.on_screen_text or "").strip()
        if texte:
            bloc = video.rasteriser_texte(
                texte, police_titre, TAILLE_BANDEAU_PX, palette.text,
                largeur_max=round(video.LARGEUR * 0.62), lignes_max=LIGNES_MAX,
            )
            interne = 36
            fond = video.rectangle_arrondi(
                (bloc.width + 2 * interne + ACCENT_PX, bloc.height + interne), 8,
                palette.bg, OPACITE_BANDEAU,
            )
            video.coller(
                fond,
                video.rectangle_arrondi((ACCENT_PX, fond.height), 0, palette.accent, 1.0),
                (0, 0),
            )
            video.coller(fond, bloc, (ACCENT_PX + interne, interne // 2))
            # Sous le tiers inférieur, au-dessus de la zone réservée aux sous-titres.
            sous_titres = channel.charte.subtitles
            reserve = sous_titres.margin_v_px + sous_titres.size_px * sous_titres.max_lines
            y = video.HAUTEUR - reserve - GARDE_SOUS_TITRES_PX - fond.height
            video.coller(calque, fond, (MARGE_PX, max(MARGE_PX, y)))
        if shot.is_sponsor:
            video.coller(
                calque, self._bandeau_divulgation(channel, police_corps), (MARGE_PX, MARGE_PX)
            )
        return calque

    def _bandeau_divulgation(self, channel: Channel, police: video.Police) -> Image.Image:
        """Bandeau « Publicité ». Le texte vient de `config/languages/<code>.yaml`."""
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
        """Rend `clips/shot_XX.mp4` : découpe, cadre, étalonnage, texte, à la durée du plan."""
        run.clips_dir.mkdir(parents=True, exist_ok=True)
        sortie = run.clip(shot.id)
        source = self._source_de(shot, run)
        calque = run.asset_dir(shot.id) / "overlay.png"
        if source.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm"}:
            return self._rendre_video(shot, source, calque, sortie)
        return self._rendre_ken_burns(shot, source, calque, sortie)

    def _source_de(self, shot: Shot, run: RunPaths) -> Path:
        """Le fichier servi au plan, quelle que soit sa nature. Absent = le plan ne peut pas être rendu."""
        dossier = run.asset_dir(shot.id)
        for nom in ("source.mp4", "source.mov", "source.m4v", "source.webm",
                    "source.jpg", "source.jpeg", "source.png", "image.png"):
            chemin = dossier / nom
            if chemin.exists() and chemin.stat().st_size > 0:
                return chemin
        raise FileNotFoundError(
            f"{shot.id} : aucun asset dans {dossier} — `prepare_assets` n'a pas été appelée"
        )

    # -- rendu vidéo ---------------------------------------------------------------------

    def _rendre_video(self, shot: Shot, source: Path, calque: Path, sortie: Path) -> Path:
        """Découpe une fenêtre de la source, la recadre, l'étalonne et y pose le texte."""
        duree = shot.duration_s
        info = video.ffprobe_clip(source)
        vitesse = ALTERNANCE_VITESSE[shot.seed % len(ALTERNANCE_VITESSE)]
        fenetre = min(duree * vitesse, max(info.duree_s - 0.05, duree * 0.5))
        debut = self._point_de_coupe(source, info.duree_s, fenetre)
        # `setpts` ramène la fenêtre sur la durée exacte du plan ; `arguments_encodage` ferme le
        # compte à l'image près. Le rapport reste dans ± 8 % : au-delà, un ralenti s'entend à
        # l'œil sur un mouvement de caméra.
        facteur = duree / fenetre if fenetre > 0 else 1.0
        chaine = (
            f"scale={video.LARGEUR}:{video.HAUTEUR}:force_original_aspect_ratio=increase"
            f":flags=bicubic,crop={video.LARGEUR}:{video.HAUTEUR},setsar=1,"
            f"setpts={facteur:.5f}*PTS,fps={video.FPS},{self.etalonnage()},{PLAGE_LIMITEE}"
        )
        entrees = ["-ss", f"{debut:.3f}", "-t", f"{fenetre + 0.2:.3f}", "-i", str(source)]
        if not calque.exists():
            arguments = entrees + ["-vf", f"{chaine},format=yuv420p"]
        else:
            filtre = (
                f"[0:v]{chaine}[base];"
                f"[1:v]{video.filtre_apparition(APPARITION_S)}[txt];"
                f"[base][txt]overlay=0:0:format=auto,format=yuv420p[v]"
            )
            arguments = entrees + [
                "-loop", "1", "-framerate", str(video.FPS), "-t", f"{duree:.3f}",
                "-i", str(calque), "-filter_complex", filtre, "-map", "[v]",
            ]
        arguments += video.arguments_encodage(sortie, duree)
        self.encoder(arguments)
        self.tracer(
            f"{shot.id} : {source.name} — fenêtre {debut:.2f}→{debut + fenetre:.2f} s "
            f"(×{1 / facteur:.2f}) sur {info.duree_s:.1f} s"
        )
        return sortie

    def _point_de_coupe(self, source: Path, duree_source: float, fenetre: float) -> float:
        """Début de la fenêtre la plus mouvementée, ou 0 si la source n'offre pas le choix.

        Le mouvement est estimé par `tblend=all_mode=difference` + `signalstats` : la moyenne de
        luminance de la différence entre images consécutives. C'est la mesure que le banc emploie
        déjà pour juger le mouvement d'un plan — l'estimation du montage et la note de sortie
        parlent donc la même langue.
        """
        if duree_source <= fenetre + MARGE_ANALYSE_S:
            return 0.0
        profil = self._profil_mouvement(source)
        if not profil:
            return 0.0
        pas = 1.0 / ANALYSE_IPS
        largeur = max(1, round(fenetre / pas))
        meilleur_debut, meilleure_somme = 0.0, -1.0
        for index in range(0, max(1, len(profil) - largeur)):
            instant = profil[index][0]
            if instant + fenetre > duree_source:
                break
            somme = sum(valeur for _, valeur in profil[index : index + largeur])
            if somme > meilleure_somme:
                meilleure_somme, meilleur_debut = somme, instant
        return round(meilleur_debut, 3)

    def _profil_mouvement(self, source: Path) -> list[tuple[float, float]]:
        """`(instant, YAVG)` toutes les 0,5 s. Mesuré une fois par fichier, puis mémorisé."""
        memo = self._profils.get(str(source))
        if memo is not None:
            return memo
        echappe = str(source).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
        commande = [
            "ffprobe", "-v", "error", "-f", "lavfi",
            "-i", (f"movie='{echappe}',fps=fps={ANALYSE_IPS},"
                   "tblend=all_mode=difference,signalstats"),
            "-show_entries", "frame=pts_time:frame_tags=lavfi.signalstats.YAVG",
            "-of", "csv=p=0",
        ]
        profil: list[tuple[float, float]] = []
        try:
            resultat = subprocess.run(commande, capture_output=True, text=True, timeout=120)
            for ligne in resultat.stdout.splitlines():
                morceaux = [m for m in ligne.strip().split(",") if m]
                if len(morceaux) >= 2:
                    try:
                        profil.append((float(morceaux[0]), float(morceaux[1])))
                    except ValueError:
                        continue
        except (OSError, subprocess.SubprocessError) as erreur:
            self.tracer(f"analyse de mouvement {source.name} : {erreur} — coupe au début")
        self._profils[str(source)] = profil
        return profil

    # -- rendu image fixe ----------------------------------------------------------------

    def _rendre_ken_burns(self, shot: Shot, image: Path, calque: Path, sortie: Path) -> Path:
        """Ken Burns sur une image fixe — course exprimée dans le repère suréchantillonné.

        Deux écarts assumés avec `illustre._rendre_ken_burns`, tous deux mesurés à l'étape 16 :
        le zoom progresse sur `on` (il ne s'accumule pas sur `zoom` à `d=1` avec `-loop 1`), et
        la course du panoramique est multipliée par le suréchantillonnage, sans quoi elle vaut le
        quart de ce qu'elle annonce. Le moteur illustré garde son rendu : il est approuvé tel quel.
        """
        duree = shot.duration_s
        images_n = max(1, round(duree * video.FPS))
        facteur = self.surechantillonnage
        grande_l, grande_h = video.LARGEUR * facteur, video.HAUTEUR * facteur
        depart, arrivee = 1.0, self.zoom_arrivee
        if shot.motion == "zoom_out" or (shot.motion == "static" and shot.seed % 2):
            depart, arrivee = arrivee, depart
        pas = abs(arrivee - depart) / images_n
        zoom = (
            f"min({depart:.3f}+on*{pas:.6f},{arrivee:.3f})" if arrivee > depart
            else f"max({depart:.3f}-on*{pas:.6f},{arrivee:.3f})"
        )
        # En pixels de l'image **d'entrée** : `zoompan` travaille sur l'image suréchantillonnée,
        # et un déplacement y vaut `facteur` fois moins à l'écran.
        course = self.course_ratio * video.LARGEUR * facteur * (1 if shot.seed % 2 == 0 else -1)
        if shot.motion == "pan":
            course *= 1.6
        mouvement = (
            f"scale={grande_l}:{grande_h}:force_original_aspect_ratio=increase:flags=bicubic,"
            f"crop={grande_l}:{grande_h},"
            f"zoompan=z='{zoom}':x='iw/2-(iw/zoom/2)+{course:.1f}*on/{images_n}':"
            f"y='ih/2-(ih/zoom/2)':d=1:s={video.LARGEUR}x{video.HAUTEUR}:fps={video.FPS},"
            f"{self.etalonnage()},{PLAGE_LIMITEE}"
        )
        entrees = [
            "-loop", "1", "-framerate", str(video.FPS), "-t", f"{duree:.3f}", "-i", str(image),
        ]
        if not calque.exists():
            arguments = entrees + ["-vf", f"{mouvement},format=yuv420p"]
        else:
            filtre = (
                f"[0:v]{mouvement}[base];"
                f"[1:v]{video.filtre_apparition(APPARITION_S)}[txt];"
                f"[base][txt]overlay=0:0:format=auto,format=yuv420p[v]"
            )
            arguments = entrees + [
                "-loop", "1", "-framerate", str(video.FPS), "-t", f"{duree:.3f}",
                "-i", str(calque), "-filter_complex", filtre, "-map", "[v]",
            ]
        arguments += video.arguments_encodage(sortie, duree)
        self.encoder(arguments)
        return sortie

    # -- divers --------------------------------------------------------------------------

    @staticmethod
    def taille_bibliotheque(racine: Path) -> tuple[int, float]:
        """Nombre de fichiers et poids en mégaoctets de `workspace/library/stock/`."""
        return stock.taille_bibliotheque(racine)


#: Ramène la vidéo en plage limitée (« tv »). **Indispensable ici, et seulement ici** : le
#: moteur illustré part de PNG, dont la conversion RGB → YUV sort déjà en plage limitée, tandis
#: que les banques servent du **JPEG et du MPEG pleine plage**. Sans cette conversion, `-pix_fmt
#: yuv420p` ne suffit pas — le flux sort étiqueté `yuvj420p`/`pc` et `verify_clip` le refuse
#: (mesuré le 18/09/2026 sur une photographie Openverse).
PLAGE_LIMITEE = "scale=out_range=tv"

#: Extensions reconnues comme vidéo par `_source_de` — gardées ici pour les tests.
EXTENSIONS_VIDEO = re.compile(r"\.(mp4|mov|m4v|webm)$", re.IGNORECASE)
