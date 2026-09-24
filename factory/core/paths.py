"""Chemins du dépôt, d'un run et de la bibliothèque partagée.

Aucun chemin n'est écrit en dur ailleurs : disposition fixée par `docs/ARCHITECTURE.md` § 3 et § 4.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

#: Racine du dépôt : deux niveaux au-dessus de ce fichier (factory/core/paths.py).
RACINE_DEFAUT = Path(__file__).resolve().parents[2]


def racine_projet() -> Path:
    """Racine du dépôt, surchargeable par la variable d'environnement `FACTORY_ROOT`."""
    return Path(os.environ.get("FACTORY_ROOT", RACINE_DEFAUT)).resolve()


def dossier_config(racine: Path | None = None) -> Path:
    """Dossier `config/`."""
    return (racine or racine_projet()) / "config"


def dossier_workspace(racine: Path | None = None) -> Path:
    """Dossier `workspace/`."""
    return (racine or racine_projet()) / "workspace"


def chemin_base(racine: Path | None = None) -> Path:
    """Chemin de `workspace/factory.db`."""
    return dossier_workspace(racine) / "factory.db"


@dataclass(frozen=True)
class RunPaths:
    """Tous les chemins d'un run, dérivés du seul `video_id`."""

    video_id: str
    racine: Path

    @classmethod
    def depuis_video_id(cls, video_id: str, racine: Path | None = None) -> RunPaths:
        """Construit les chemins d'un run à partir de son identifiant."""
        return cls(video_id=video_id, racine=dossier_workspace(racine) / "runs" / video_id)

    # --- fichiers racine du run ---
    @property
    def spec(self) -> Path:
        """`spec.json`."""
        return self.racine / "spec.json"

    @property
    def research(self) -> Path:
        """`research.json`."""
        return self.racine / "research.json"

    @property
    def script(self) -> Path:
        """`script.json`."""
        return self.racine / "script.json"

    @property
    def review(self) -> Path:
        """`review.json`."""
        return self.racine / "review.json"

    @property
    def words(self) -> Path:
        """`words.json`."""
        return self.racine / "words.json"

    @property
    def subtitles_srt(self) -> Path:
        """`subtitles.srt` — piste de distribution."""
        return self.racine / "subtitles.srt"

    @property
    def subtitles_ass(self) -> Path:
        """`subtitles.ass` — incrustation."""
        return self.racine / "subtitles.ass"

    @property
    def shotlist(self) -> Path:
        """`shotlist.json`."""
        return self.racine / "shotlist.json"

    @property
    def metadata(self) -> Path:
        """`metadata.json`."""
        return self.racine / "metadata.json"

    @property
    def qc(self) -> Path:
        """`qc.json`."""
        return self.racine / "qc.json"

    @property
    def publish(self) -> Path:
        """`publish.json`."""
        return self.racine / "publish.json"

    @property
    def manifest(self) -> Path:
        """`manifest.json`."""
        return self.racine / "manifest.json"

    @property
    def events(self) -> Path:
        """`events.jsonl` — append-only."""
        return self.racine / "events.jsonl"

    @property
    def publication_md(self) -> Path:
        """`publication.md` — pense-bête des gestes manuels."""
        return self.racine / "publication.md"

    @property
    def video_nomusic(self) -> Path:
        """`video_nomusic.mp4`."""
        return self.racine / "video_nomusic.mp4"

    @property
    def final(self) -> Path:
        """`final.mp4`."""
        return self.racine / "final.mp4"

    @property
    def thumbnail(self) -> Path:
        """`thumbnail.png` — copie de la variante retenue, jamais un lien."""
        return self.racine / "thumbnail.png"

    # --- dossiers ---
    @property
    def voice_dir(self) -> Path:
        """`voice/`."""
        return self.racine / "voice"

    @property
    def voice_wav(self) -> Path:
        """`voice/voice.wav`."""
        return self.voice_dir / "voice.wav"

    @property
    def timings(self) -> Path:
        """`voice/timings.json`."""
        return self.voice_dir / "timings.json"

    @property
    def assets_dir(self) -> Path:
        """`assets/`."""
        return self.racine / "assets"

    @property
    def review_visual(self) -> Path:
        """`assets/review_visual.json` — file de relecture des plans à personnage."""
        return self.assets_dir / "review_visual.json"

    @property
    def clips_dir(self) -> Path:
        """`clips/`."""
        return self.racine / "clips"

    @property
    def thumbnails_dir(self) -> Path:
        """`thumbnails/`."""
        return self.racine / "thumbnails"

    @property
    def thumbnails_json(self) -> Path:
        """`thumbnails/thumbnails.json`."""
        return self.thumbnails_dir / "thumbnails.json"

    @property
    def done_dir(self) -> Path:
        """`.done/` — marqueurs d'idempotence."""
        return self.racine / ".done"

    # --- chemins paramétrés ---
    def segment_wav(self, index: int) -> Path:
        """`voice/segment_XX.wav`."""
        return self.voice_dir / f"segment_{index:02d}.wav"

    def asset_dir(self, shot_id: str) -> Path:
        """`assets/<shot_id>/`."""
        return self.assets_dir / shot_id

    def licence(self, shot_id: str) -> Path:
        """`assets/<shot_id>/licence.json`."""
        return self.asset_dir(shot_id) / "licence.json"

    def clip(self, shot_id: str) -> Path:
        """`clips/<shot_id>.mp4`."""
        return self.clips_dir / f"{shot_id}.mp4"

    def variante_miniature(self, numero: int) -> Path:
        """`thumbnails/variant_N.png`."""
        return self.thumbnails_dir / f"variant_{numero}.png"

    def done(self, etape: str) -> Path:
        """`.done/<etape>.done`."""
        return self.done_dir / f"{etape}.done"

    def export(self, racine: Path | None = None) -> Path:
        """`workspace/export/<video_id>.mp4`."""
        return dossier_workspace(racine) / "export" / f"{self.video_id}.mp4"

    def creer(self) -> RunPaths:
        """Crée l'arborescence du run. Idempotent."""
        for dossier in (
            self.racine, self.voice_dir, self.assets_dir,
            self.clips_dir, self.thumbnails_dir, self.done_dir,
        ):
            dossier.mkdir(parents=True, exist_ok=True)
        return self

    def existe(self) -> bool:
        """Vrai si le dossier du run existe déjà sur disque."""
        return self.racine.is_dir()


@dataclass(frozen=True)
class LibraryPaths:
    """Chemins de la bibliothèque partagée `workspace/library/`."""

    racine: Path

    @classmethod
    def depuis_racine(cls, racine: Path | None = None) -> LibraryPaths:
        """Construit les chemins de la bibliothèque."""
        return cls(racine=dossier_workspace(racine) / "library")

    SOUS_DOSSIERS = ("images", "stock", "music", "sfx", "characters", "intros")

    @property
    def images(self) -> Path:
        """`library/images/`."""
        return self.racine / "images"

    @property
    def stock(self) -> Path:
        """`library/stock/`."""
        return self.racine / "stock"

    @property
    def music(self) -> Path:
        """`library/music/`."""
        return self.racine / "music"

    @property
    def sfx(self) -> Path:
        """`library/sfx/`."""
        return self.racine / "sfx"

    @property
    def characters(self) -> Path:
        """`library/characters/` — propre à une chaîne, jamais partagé."""
        return self.racine / "characters"

    @property
    def intros(self) -> Path:
        """`library/intros/`."""
        return self.racine / "intros"

    @property
    def cadence(self) -> Path:
        """`library/cadence.json` — seule source de vérité sur « peut-on publier maintenant »."""
        return self.racine / "cadence.json"

    def licence(self, fichier: Path) -> Path:
        """`licence.json` frère d'un fichier de la bibliothèque."""
        return fichier.with_name("licence.json")

    def creer(self) -> LibraryPaths:
        """Crée l'arborescence de la bibliothèque. Idempotent."""
        for nom in self.SOUS_DOSSIERS:
            (self.racine / nom).mkdir(parents=True, exist_ok=True)
        return self


def assets_exclus(video_id: str, racine=None) -> set[str]:
    """Assets interdits à ce run — `assets/exclus.json`, écrit par la régénération (22.2).

    Vide dans le cas normal. Le remède « variété visuelle faible » l'écrit avant de rejouer
    `shotlist` : sans lui, la reprise redemanderait exactement les mêmes images à la
    bibliothèque, puisque le rejeu du même run est précisément le cas où `_reutilisable`
    autorise la réutilisation (objection 18 d'`INTERFACES`). Le remède a besoin de
    l'exception inverse.
    """
    import json as _json

    fichier = RunPaths.depuis_video_id(video_id, racine).assets_dir / "exclus.json"
    if not fichier.exists():
        return set()
    try:
        charge = _json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    return {str(a) for a in (charge.get("asset_ids") or [])}
