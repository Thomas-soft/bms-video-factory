"""Moteur « cartes » — texte de charte sur fond animé, **ffmpeg pur, aucun pixel généré par IA**.

C'est le moteur interne de mise au point : il porte le découpage et l'interface, il donne une
vidéo complète en quelques minutes, et il **ne doit jamais être publié tel quel** — « scrolling
text with minimal or no narrative » est littéralement le cas visé par la politique de contenu
inauthentique (`ARCHITECTURE.md` § 5).

Un plan = trois couches, dans cet ordre :

1. **Fond** — dégradé animé lent entre le fond et l'accent de la charte, éventuellement mis en
   mouvement (`zoompan`). Aucun détail : c'est pourquoi le suréchantillonnage ×4 ne lui est pas
   appliqué, il n'y a rien à faire trembler.
2. **Forme géométrique** — une barre d'accent qui glisse (`drawbox` à expression de temps). Subtile
   : elle donne du mouvement quand le plan est `static`, sans disputer la lecture au texte.
3. **Carte** — un PNG RGBA rastérisé en amont (gabarit + texte + marges), composé par `overlay`
   avec une apparition par alpha. Trois gabarits en alternance : `plein`, `bandeau_bas`,
   `carte_centrale`.

Un plan `is_sponsor` reçoit **en plus** un bandeau de divulgation, sans fondu et sur toute la durée
du plan : la loi française 2023-451 exige la mention « Publicité » **pendant** la promotion, pas
après une rampe d'alpha (`CONFORMITE.md` § 3).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from factory import video
from factory.core.models import Asset, Channel, Shot, Shotlist
from factory.core.paths import RunPaths
from factory.styles.base import MoteurBase

#: Marge de sécurité par défaut, en pixels — surchargée par `config/styles/cartes.yaml`.
MARGE_PX = 96
#: Tailles par défaut du texte, en pixels.
TAILLE_TITRE_PX = 88
TAILLE_CORPS_PX = 56
#: Un texte à l'écran tient en trois lignes ou il n'est pas un texte à l'écran.
LIGNES_MAX = 3
#: Durée de l'apparition de la carte, en secondes.
APPARITION_S = 0.45
#: Opacité du gabarit `bandeau_bas` et de la carte centrale.
OPACITE_CARTE = 0.86
#: Licence des cartes : elles ne sont faites que de la charte et d'une police OFL.
LICENCE_CARTE = "OFL-1.1"
LICENCE_URL = "https://openfontlicense.org/open-font-license-official-text/"


@dataclass
class CartesEngine(MoteurBase):
    """Moteur de style « cartes » (`STYLE_ENGINES["cartes"]`)."""

    name: str = "cartes"
    backend: str = "ffmpeg"

    # -- géométrie -----------------------------------------------------------------------

    @property
    def marge(self) -> int:
        return int(self.param("card.marge_px", MARGE_PX) or MARGE_PX)

    @property
    def taille_titre(self) -> int:
        return int(self.param("card.taille_titre_px", TAILLE_TITRE_PX) or TAILLE_TITRE_PX)

    @property
    def taille_corps(self) -> int:
        return int(self.param("card.taille_corps_px", TAILLE_CORPS_PX) or TAILLE_CORPS_PX)

    @staticmethod
    def gabarit_de(shot: Shot) -> str:
        """Le gabarit est porté par `asset_request.prompt_or_keywords` pour un asset `card`."""
        demande = shot.asset_request.prompt_or_keywords.strip()
        return demande if demande in {"plein", "bandeau_bas", "carte_centrale"} else "plein"

    # -- prepare_assets ------------------------------------------------------------------

    def prepare_assets(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths
    ) -> list[Asset]:
        """Rastérise la carte de chaque plan en `assets/<shot>/card.png` et sa licence.

        Idempotente au plan près : une carte déjà là n'est pas refaite. Aucun modèle n'est chargé,
        donc aucun sous-processus n'est nécessaire — la règle « un modèle résident » ne mord pas ici.
        """
        police_titre = self.police_titre(channel)
        police_corps = self.police_corps(channel)
        assets: list[Asset] = []
        for shot in shotlist.shots:
            dossier = run.asset_dir(shot.id)
            dossier.mkdir(parents=True, exist_ok=True)
            fichier = dossier / "card.png"
            if not fichier.exists():
                calque = self._composer_carte(shot, channel, police_titre, police_corps)
                calque.save(fichier, "PNG")
            licence = run.licence(shot.id)
            asset = Asset(
                asset_id=self.identifiant_asset(fichier),
                path=f"assets/{shot.id}/card.png",
                provider="charte",
                # La source d'une carte est la charte de la chaîne, pas une URL : le champ dit
                # d'où vient le pixel, et c'est vérifiable dans le dépôt.
                source_url=f"config/channels/{channel.id}.yaml#charte@{channel.charte.version}",
                author=f"BMS ({channel.name})",
                licence=LICENCE_CARTE,
                licence_url=LICENCE_URL,
                attribution_line=None,
                downloaded_at=self.maintenant(),
                person_release=None,
                generator=None,
                realistic=False,
                has_text=bool(shot.on_screen_text) or shot.is_sponsor,
                c2pa_present=False,
            )
            licence.write_text(
                json.dumps(asset.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            assets.append(asset)
        return assets

    def _composer_carte(
        self, shot: Shot, channel: Channel, police_titre: video.Police,
        police_corps: video.Police,
    ) -> Image.Image:
        """Le calque complet d'un plan : gabarit, texte à l'écran, bandeau de divulgation."""
        palette = channel.charte.palette
        calque = Image.new("RGBA", (video.LARGEUR, video.HAUTEUR), (0, 0, 0, 0))
        gabarit = self.gabarit_de(shot)
        marge = self.marge
        largeur_utile = video.LARGEUR - 2 * marge

        if gabarit == "bandeau_bas":
            hauteur_bandeau = round(video.HAUTEUR * 0.30)
            bandeau = video.rectangle_arrondi(
                (video.LARGEUR, hauteur_bandeau), 0, palette.bg, OPACITE_CARTE
            )
            video.coller(calque, bandeau, (0, video.HAUTEUR - hauteur_bandeau))
            trait = video.rectangle_arrondi((video.LARGEUR, 6), 0, palette.accent, 1.0)
            video.coller(calque, trait, (0, video.HAUTEUR - hauteur_bandeau))
            zone = (marge, video.HAUTEUR - hauteur_bandeau, largeur_utile, hauteur_bandeau)
        elif gabarit == "carte_centrale":
            carte_l = round(video.LARGEUR * 0.72)
            carte_h = round(video.HAUTEUR * 0.44)
            carte = video.rectangle_arrondi(
                (carte_l, carte_h), 36, palette.bg, OPACITE_CARTE,
                bordure=palette.accent, bordure_px=4,
            )
            origine = ((video.LARGEUR - carte_l) // 2, (video.HAUTEUR - carte_h) // 2)
            video.coller(calque, carte, origine)
            zone = (origine[0] + marge // 2, origine[1], carte_l - marge, carte_h)
        else:  # plein
            zone = (marge, 0, largeur_utile, video.HAUTEUR)

        texte = shot.on_screen_text
        if texte:
            bloc = video.rasteriser_texte(
                texte.strip(), police_titre, self.taille_titre, palette.text,
                largeur_max=zone[2], lignes_max=LIGNES_MAX,
                contour=palette.text_outline, contour_px=3,
            )
            x = zone[0] + (zone[2] - bloc.width) // 2
            y = zone[1] + (zone[3] - bloc.height) // 2
            x, y = max(marge // 2, x), max(marge // 2, y)
            video.coller(calque, bloc, (x, y))
            # Le souligné est centré **sous le bloc de texte**, pas calé à sa gauche : décalé, il
            # se lit comme un défaut d'alignement et non comme un accent de charte.
            largeur_souligne = max(80, round(bloc.width * 0.35))
            video.coller(
                calque,
                video.rectangle_arrondi((largeur_souligne, 8), 4, palette.highlight, 1.0),
                (x + (bloc.width - largeur_souligne) // 2,
                 min(video.HAUTEUR - marge, y + bloc.height + 14)),
            )

        if shot.is_sponsor:
            video.coller(calque, self._bandeau_divulgation(channel, police_corps), (marge, marge))
        return calque

    def _bandeau_divulgation(self, channel: Channel, police: video.Police) -> Image.Image:
        """Bandeau « Publicité » — le texte vient de `config/languages/<code>.yaml`, jamais du code.

        Le moteur ne connaît pas la langue : la phrase lui est **passée** à la construction
        (`texte_divulgation`), par l'étape `render` qui, elle, lit `config/languages/<code>.yaml`.
        """
        texte = self.texte_divulgation or "Publicité"
        palette = channel.charte.palette
        bloc = video.rasteriser_texte(
            texte.upper(), police, round(self.taille_corps * 0.62), palette.bg,
            largeur_max=round(video.LARGEUR * 0.4), lignes_max=1,
        )
        marge_interne = 28
        fond = video.rectangle_arrondi(
            (bloc.width + 2 * marge_interne, bloc.height + marge_interne), 12,
            palette.highlight, 1.0,
        )
        video.coller(fond, bloc, (marge_interne, marge_interne // 2))
        return fond

    # -- render_shot ---------------------------------------------------------------------

    def render_shot(
        self, shot: Shot, assets: list[Asset], channel: Channel, run: RunPaths
    ) -> Path:
        """Rend `clips/shot_XX.mp4` : dégradé animé + forme mobile + carte en apparition."""
        run.clips_dir.mkdir(parents=True, exist_ok=True)
        sortie = run.clip(shot.id)
        carte = run.asset_dir(shot.id) / "card.png"
        if not carte.exists():
            raise FileNotFoundError(
                f"{shot.id} : carte absente ({carte}) — `prepare_assets` n'a pas été appelée"
            )
        palette = channel.charte.palette
        duree = shot.duration_s
        # La graine du plan décide de la rotation du dégradé et du sens de la barre : deux plans
        # voisins ne se ressemblent pas, et le même plan rejoué est identique au pixel.
        variation = shot.seed % 4
        # L'accent pur en aplat plein cadre écrase le texte : le fond est teinté, pas coloré.
        teintes = [
            video.melanger(palette.bg, palette.text_outline, 0.55),
            video.melanger(palette.bg, palette.accent, 0.34),
        ]
        if variation % 2:
            teintes.reverse()

        fond = video.source_degrade(
            teintes, duree_s=duree, vitesse=0.008 + 0.004 * (variation / 3), graine=shot.seed,
            diagonale=variation,
        )
        mouvement = video.filtre_zoompan(shot.motion, duree, surechantillonnage=1)
        sens = 1 if variation % 2 == 0 else -1
        largeur_barre = 420
        depart = -largeur_barre if sens > 0 else video.LARGEUR
        vitesse_barre = (video.LARGEUR + largeur_barre) / max(duree, 0.1) * sens
        hauteur_barre = round(video.HAUTEUR * (0.14 if variation < 2 else 0.86))
        barre = (
            f"drawbox=x='{depart}+{vitesse_barre:.2f}*t':y={hauteur_barre}"
            f":w={largeur_barre}:h=8:color={palette.highlight}@0.45:t=fill"
        )

        chaine = [fond]
        if mouvement:
            chaine.append(mouvement)
        chaine.append(barre)
        filtre = (
            f"{','.join(chaine)},format=rgba[bg];"
            f"[0:v]{video.filtre_apparition(APPARITION_S)}[carte];"
            f"[bg][carte]overlay=0:0:format=auto,format=yuv420p[v]"
        )
        arguments = [
            "-loop", "1", "-framerate", str(video.FPS), "-t", f"{duree:.3f}", "-i", str(carte),
            "-filter_complex", filtre, "-map", "[v]",
            *video.arguments_encodage(sortie, duree),
        ]
        self.encoder(arguments)
        return sortie

    # -- divers --------------------------------------------------------------------------

    @staticmethod
    def empreinte_gabarit(shot: Shot) -> str:
        """Empreinte courte du contenu visuel d'un plan, pour le journal."""
        brut = f"{shot.id}|{shot.on_screen_text}|{shot.asset_request.prompt_or_keywords}"
        return hashlib.sha256(brut.encode("utf-8")).hexdigest()[:8]
