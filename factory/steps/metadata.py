"""`factory metadata` — la fiche que `publish` enverra à l'API, mot pour mot.

L'étape lit le run, applique la règle de conformité, et laisse `factory/editorial/seo.py`
composer. Ce qui reste ici est ce que seul le run sait : quels assets ont été générés, lesquels
figurent une personne, et ce que le manifeste doit porter ensuite.

- **`contains_synthetic_media` n'est pas une opinion** : c'est la règle de `CONFORMITE` § 3
  couche 1 appliquée aux assets du run — `realistic` est posé par le module qui a produit
  l'image, et agrégé ici avec le motif écrit. L'assistance de production (script, voix,
  illustration non réaliste) ne le déclenche pas ; elle est dite en description.
- **`virtual_images_mention` est une condition distincte** (couche 3) : une image IA figurant
  un visage ou une silhouette, réaliste ou non. Une illustration de personnage la déclenche.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from factory.core import config as config_module
from factory.core import db, runs
from factory.core.models import (
    Asset,
    LignesDivulgation,
    Research,
    SceneSynthetique,
    Script,
    Shotlist,
    Timings,
    VideoMetadata,
    VideoSpec,
)
from factory.core.paths import RunPaths, racine_projet
from factory.editorial import seo
from factory.editorial.seo import (
    CHAPITRES_MAX,
    DESCRIPTION_MAX_OCTETS,
    ECART_CHAPITRE_MIN_S,
    TAGS_MAX_CARACTERES,
    chapitres_depuis_timings,
)

__all__ = [
    "CHAPITRES_MAX",
    "DESCRIPTION_MAX_OCTETS",
    "ECART_CHAPITRE_MIN_S",
    "TAGS_MAX_CARACTERES",
    "ResultatMetadata",
    "chapitres_depuis_timings",
    "evaluer_synthetique",
    "executer",
]


@dataclass
class ResultatMetadata:
    """Ce que l'étape a produit, pour la CLI et le journal."""

    metadata: VideoMetadata
    chemin: Path
    secondes: float
    alertes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------------------
# Conformité — § 3 appliqué au style et aux intentions visuelles
# --------------------------------------------------------------------------------------


def evaluer_synthetique(
    assets: list[Asset], shotlist: Shotlist, style_id: str
) -> tuple[bool, str | None, bool, list[SceneSynthetique]]:
    """Applique la règle de `CONFORMITE` § 3 aux assets du run.

    Renvoie `(contains_synthetic_media, reason, virtual_images_mention, scènes)`. La règle
    est mécanique : un asset **généré** et marqué `realistic` déclenche le drapeau ; un asset
    généré figurant une personne déclenche la mention « Images virtuelles », réaliste ou non.
    """
    personnes = {s.id: s.asset_request.contains_person for s in shotlist.shots}
    scenes: list[SceneSynthetique] = []
    for asset in assets:
        if asset.generator is None:
            continue
        shot = Path(asset.path).parent.name
        scenes.append(SceneSynthetique(
            scene_id=shot, generator=asset.generator.model,
            prompt_hash=asset.generator.prompt_hash, realistic=bool(asset.realistic),
        ))
    realistes = [s for s in scenes if s.realistic]
    virtuelles = any(personnes.get(s.scene_id, False) for s in scenes)
    if not realistes:
        return False, None, virtuelles, scenes
    modeles = sorted({s.generator for s in realistes})
    motif = (
        f"{len(realistes)} plan(s) générés en rendu réaliste par {', '.join(modeles)} "
        f"(style « {style_id} ») : {', '.join(s.scene_id for s in realistes[:8])}"
        f"{'…' if len(realistes) > 8 else ''} — CONFORMITE § 3 couche 1, scène réaliste générée."
    )
    return True, motif, virtuelles, scenes


# --------------------------------------------------------------------------------------
# Étape
# --------------------------------------------------------------------------------------


def executer(
    video_id: str, racine: Path | None = None, reseau: bool = True
) -> ResultatMetadata:
    """Écrit `metadata.json` et reporte les drapeaux de conformité au manifeste."""
    t0 = time.perf_counter()
    racine = racine or racine_projet()
    chemins = RunPaths.depuis_video_id(video_id, racine)
    for fichier in (chemins.spec, chemins.script, chemins.timings, chemins.shotlist):
        if not fichier.exists():
            raise FileNotFoundError(f"metadata : {fichier.name} exigé ({chemins.racine})")

    spec = VideoSpec.model_validate_json(chemins.spec.read_text(encoding="utf-8"))
    script = Script.model_validate_json(chemins.script.read_text(encoding="utf-8"))
    timings = Timings.model_validate_json(chemins.timings.read_text(encoding="utf-8"))
    shotlist = Shotlist.model_validate_json(chemins.shotlist.read_text(encoding="utf-8"))
    research = (
        Research.model_validate_json(chemins.research.read_text(encoding="utf-8"))
        if chemins.research.exists() else None
    )
    manifest = runs.charger_manifest(video_id, racine)

    cfg = config_module.charger(racine, strict=False)
    channel = cfg.get_channel(spec.channel_id)
    langue = cfg.langue_de(channel)

    titre = manifest.decisions.title_chosen
    if not titre:
        raise FileNotFoundError(
            "metadata : aucun titre au manifeste — `factory thumbnail` (titles) passe avant"
        )

    synthetique, motif, virtuelles, scenes = evaluer_synthetique(
        manifest.decisions.assets, shotlist, channel.style
    )
    metadata, liens, alertes = seo.composer(
        spec=spec, script=script, timings=timings, research=research, manifest=manifest,
        channel=channel, cfg=cfg, langue=langue, titre=titre,
        miniature=manifest.decisions.thumbnail_chosen, synthetique=synthetique,
        motif_synthetique=motif, virtuelles=virtuelles, racine=racine, reseau=reseau,
    )
    runs.ecrire_json(chemins.metadata, metadata)

    # Report au manifeste : les drapeaux de conformité sont calculés ici, pas à l'upload.
    manifest.conformite.contains_synthetic_media = synthetique
    manifest.conformite.contains_synthetic_media_reason = motif
    manifest.conformite.synthetic_scenes = scenes
    manifest.conformite.virtual_images_mention = virtuelles
    manifest.conformite.paid_promotion = metadata.paid_promotion
    manifest.conformite.affiliate_links = liens
    if metadata.paid_promotion or virtuelles:
        manifest.conformite.disclosure_lines = {
            channel.lang: LignesDivulgation(
                description_line=(metadata.description_blocks.disclosure
                                  or langue.disclosure.virtual_images),
                overlay_text=(langue.disclosure.overlay_generic if metadata.paid_promotion
                              else langue.disclosure.virtual_images),
                spoken_line=(script.disclosure_lines.spoken_line
                             if script.disclosure_lines else langue.disclosure.overlay_generic),
            )
        }
    manifest.execution.timings["metadata"] = round(time.perf_counter() - t0, 2)
    runs.ecrire_json(chemins.manifest, manifest)
    conn = db.ouvrir(None if racine is None else racine / "workspace" / "factory.db")
    db.migrer(conn)
    runs.enregistrer(conn, spec, manifest, racine)
    conn.close()

    return ResultatMetadata(
        metadata=metadata, chemin=chemins.metadata,
        secondes=time.perf_counter() - t0, alertes=alertes,
    )
