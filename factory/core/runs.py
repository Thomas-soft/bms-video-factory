"""Index des runs en base — écriture et lectures dont les étapes 10 et suivantes ont besoin.

Les fichiers restent la source de vérité (`ARCHITECTURE` § 1.8) : cette table est un index,
que `factory queue reindex` reconstruira en relisant les manifestes.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from factory.core.models import RunManifest, VideoSpec
from factory.core.paths import RunPaths


def maintenant() -> str:
    """Horodatage ISO-8601 UTC au format imposé par `INTERFACES` § 0."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def enregistrer(
    conn: sqlite3.Connection, spec: VideoSpec, manifest: RunManifest, racine: Path | None = None
) -> None:
    """Insère ou met à jour la ligne `runs` d'un run à partir de ses fichiers."""
    chemins = RunPaths.depuis_video_id(spec.video_id, racine)
    decisions, execution = manifest.decisions, manifest.execution
    conn.execute(
        """
        INSERT INTO runs (
            video_id, parent_id, channel_id, lang, niche, style, template_id, charte_version,
            run_state, publish_state, publish_path, topic_sujet, topic_source, topic_score,
            hook_type, voice_id, duration_s, cut_rhythm_target_s, density_facts_per_min,
            open_loops_planted, created_at, updated_at, manifest_path, manifest_json
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(video_id) DO UPDATE SET
            run_state = excluded.run_state,
            publish_state = excluded.publish_state,
            topic_sujet = excluded.topic_sujet,
            topic_source = excluded.topic_source,
            topic_score = excluded.topic_score,
            hook_type = excluded.hook_type,
            duration_s = excluded.duration_s,
            cut_rhythm_target_s = excluded.cut_rhythm_target_s,
            density_facts_per_min = excluded.density_facts_per_min,
            open_loops_planted = excluded.open_loops_planted,
            updated_at = excluded.updated_at,
            manifest_json = excluded.manifest_json
        """,
        (
            spec.video_id, spec.parent_id, spec.channel_id, spec.lang, spec.niche, spec.style,
            manifest.identite.template_id, manifest.identite.charte_version,
            execution.run_state, manifest.conformite.publish_state, manifest.conformite.publish_path,
            decisions.topic.sujet, decisions.topic.source, decisions.topic.evidence.score,
            decisions.hook_type or None, decisions.voice_id, decisions.duration_s,
            decisions.cut_rhythm_target_s, decisions.density_facts_per_min,
            decisions.open_loops.planted, spec.created_at, maintenant(), str(chemins.manifest),
            manifest.model_dump_json(exclude_none=False),
        ),
    )
    conn.commit()


def sujets_deja_pris(conn: sqlite3.Connection, channel_id: str, lang: str) -> set[str]:
    """Sujets déjà employés par cette chaîne **ou** par une autre chaîne de la même langue.

    C'est la règle anti-clonage de `CONFORMITE` § 5 appliquée en amont : deux chaînes
    francophones ne traitent jamais le même sujet ; une chaîne anglophone le peut.
    """
    lignes = conn.execute(
        "SELECT topic_sujet FROM runs WHERE topic_sujet IS NOT NULL AND (channel_id = ? OR lang = ?)",
        (channel_id, lang),
    ).fetchall()
    return {ligne[0].strip().lower() for ligne in lignes if ligne[0]}


def charger_spec(video_id: str, racine: Path | None = None) -> VideoSpec:
    """Relit le `spec.json` d'un run."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    if not chemins.spec.exists():
        raise FileNotFoundError(f"run inconnu : {chemins.spec}")
    return VideoSpec.model_validate_json(chemins.spec.read_text(encoding="utf-8"))


def charger_manifest(video_id: str, racine: Path | None = None) -> RunManifest:
    """Relit le `manifest.json` d'un run."""
    chemins = RunPaths.depuis_video_id(video_id, racine)
    return RunManifest.model_validate_json(chemins.manifest.read_text(encoding="utf-8"))


def ecrire_json(chemin: Path, modele: object) -> None:
    """Écrit un modèle pydantic en JSON indenté et stable."""
    charge = modele.model_dump(mode="json")  # type: ignore[attr-defined]
    chemin.write_text(json.dumps(charge, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def dernier_gabarit(conn, channel_id: str, sauf: str | None = None) -> str | None:
    """`template_id` du run le plus récent de la chaîne (rotation des gabarits, étape 29)."""
    ligne = conn.execute(
        "SELECT template_id FROM runs WHERE channel_id = ? AND video_id != ? "
        "ORDER BY created_at DESC LIMIT 1", (channel_id, sauf or "")).fetchone()
    return ligne[0] if ligne else None


def gabarit_suivant(conn, channel_id: str, gabarits: list[str]) -> str:
    """Le gabarit qui suit celui du dernier run : jamais deux fois le même de suite (§ 5)."""
    dernier = dernier_gabarit(conn, channel_id)
    if dernier not in gabarits:
        return gabarits[0]
    return gabarits[(gabarits.index(dernier) + 1) % len(gabarits)]


def dernier_gabarit_avant(conn, channel_id: str, video_id: str) -> str | None:
    """`template_id` du run de la chaîne créé juste avant `video_id`."""
    ligne = conn.execute(
        "SELECT template_id FROM runs WHERE channel_id = ? AND created_at < "
        "(SELECT created_at FROM runs WHERE video_id = ?) ORDER BY created_at DESC LIMIT 1",
        (channel_id, video_id)).fetchone()
    return ligne[0] if ligne else None
