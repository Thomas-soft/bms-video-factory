"""Interface `StyleEngine` et socle commun aux moteurs (`INTERFACES.md` § 3).

Deux méthodes, et rien d'autre. Le moteur ne connaît **ni la langue, ni la conformité, ni la
publication** : le découpage, les timings, les sous-titres, le montage, la miniature et le QC
vivent hors des moteurs. Ce qu'un moteur reçoit, il le reçoit en paramètre.

`MoteurBase` n'est pas dans le contrat : c'est l'outillage que tout moteur ffmpeg répète — charte,
palette, polices, chemins, journal, vérification `ffprobe`. Un moteur peut l'ignorer ; il doit
seulement satisfaire le `Protocol`.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Literal, Protocol, runtime_checkable

from factory import video
from factory.core.models import Asset, Channel, Charte, Shot, Shotlist, Style
from factory.core.paths import RunPaths, racine_projet


@runtime_checkable
class StyleEngine(Protocol):
    """Contrat d'un moteur de style. Ajouter un style = un YAML + une classe au registre."""

    name: str
    backend: Literal["ffmpeg", "revideo"]

    def prepare_assets(
        self, shotlist: Shotlist, channel: Channel, run: RunPaths
    ) -> list[Asset]:
        """Acquiert ou génère les assets de tous les plans, écrit `assets/<shot>/licence.json`.

        Un sous-processus par modèle chargé, jamais deux modèles résidents (`ARCHITECTURE` § 1.3).
        Doit être idempotente au plan près : un plan déjà servi n'est pas régénéré.
        """

    def render_shot(
        self, shot: Shot, assets: list[Asset], channel: Channel, run: RunPaths
    ) -> Path:
        """Rend un plan en `clips/shot_XX.mp4` au contrat de format, et rend son chemin.

        Ne lit que `shot`, `assets`, `channel.charte` et `run`. Aucun état entre deux appels.
        """


@dataclass
class MoteurBase:
    """Socle des moteurs à backend ffmpeg : charte, polices, chemins, journal, vérification.

    `journal` est un fichier ouvert en écriture : **toute** sortie ffmpeg y va, jamais à l'écran
    (`CLAUDE.md` § 2). `params` vient de `config/styles/<id>.yaml`, jamais d'une constante.
    """

    style: Style
    racine: Path = field(default_factory=racine_projet)
    journal: IO[str] | None = None
    #: Phrase de divulgation à incruster sur un plan `is_sponsor`. Le moteur ne connaît pas la
    #: langue : le pipeline la lit dans `config/languages/<code>.yaml` et la lui passe ici.
    texte_divulgation: str | None = None

    @property
    def params(self) -> dict:
        """Paramètres du style, tels que la configuration les déclare."""
        return self.style.params or {}

    def param(self, chemin: str, defaut: object = None) -> object:
        """Lit `params` en notation pointée : `param("card.marge_px", 96)`."""
        courant: object = self.params
        for cle in chemin.split("."):
            if not isinstance(courant, dict) or cle not in courant:
                return defaut
            courant = courant[cle]
        return courant

    # -- charte -------------------------------------------------------------------------

    @staticmethod
    def charte_de(channel: Channel) -> Charte:
        """La charte d'une chaîne ; aucune valeur visuelle n'est lue ailleurs."""
        return channel.charte

    def police_titre(self, channel: Channel) -> video.Police:
        """Police des titres, résolue en fichier OFL."""
        return video.resoudre_police(channel.charte.fonts.title, self.racine)

    def police_corps(self, channel: Channel) -> video.Police:
        """Police de corps, résolue en fichier OFL."""
        return video.resoudre_police(channel.charte.fonts.body, self.racine)

    def transition_permise(self, channel: Channel, transition: str) -> bool:
        """Une transition hors `charte.transitions[]` n'est pas employable par le moteur."""
        return transition in set(channel.charte.transitions) | {"cut", "none"}

    # -- assets --------------------------------------------------------------------------

    @staticmethod
    def identifiant_asset(chemin: Path) -> str:
        """`sha256(fichier)[:16]` — identifiant stable, réutilisable en bibliothèque."""
        empreinte = hashlib.sha256(chemin.read_bytes()).hexdigest()
        return empreinte[:16]

    @staticmethod
    def maintenant() -> str:
        """Horodatage ISO-8601 UTC, comme tous les fichiers du run."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # -- rendu ---------------------------------------------------------------------------

    def encoder(self, arguments: list[str]) -> float:
        """Lance ffmpeg avec la sortie dirigée vers le journal ; rend le temps écoulé."""
        return video.lancer_ffmpeg(arguments, self.journal)

    def verify_clip(self, chemin: Path, duree_attendue_s: float) -> list[str]:
        """Écarts au contrat de format d'un clip, mesurés par `ffprobe`. Vide = conforme."""
        return video.verify_clip(chemin, duree_attendue_s)

    def tracer(self, message: str) -> None:
        """Une ligne dans le journal de l'étape — pas à l'écran."""
        if self.journal is not None:
            self.journal.write(message.rstrip() + "\n")
            self.journal.flush()
