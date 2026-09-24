"""Rotation des miniatures à J+7 (étape 26) : qui basculer, vers quelle variante.

Ne réécrit jamais `decisions.thumbnail_chosen` : c'est la miniature INITIALE qui est le facteur
appris (la réécrire ferait fuiter un choix post-publication dans les prédicteurs).
"""

from __future__ import annotations

import json
import sqlite3
import statistics
import zlib
from pathlib import Path
from typing import Any

from factory.analytics import weights as wmod
from factory.editorial import thumbnails_variants as tv


def propositions(conn: sqlite3.Connection, racine: Path) -> list[dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    try:
        lignes = [dict(x) for x in conn.execute(
            """SELECT v.video_id, v.channel_id, v.ctr_7d, r.manifest_path
                 FROM v_video_perf v LEFT JOIN runs r ON r.video_id = v.video_id
                WHERE v.complete_7d = 1""")]
    except sqlite3.OperationalError:
        return []
    poids = wmod.charger(racine)
    sortie = []
    for x in lignes:
        autres = [o["ctr_7d"] for o in lignes if o["channel_id"] == x["channel_id"]
                  and o["video_id"] != x["video_id"] and o["ctr_7d"] is not None]
        mediane = statistics.median(autres) if autres else None
        rotation, gabarits = {}, {}
        if x.get("manifest_path"):
            m = Path(x["manifest_path"])
            m = m if m.is_absolute() else racine / m
            if m.is_file():
                d = json.loads(m.read_text("utf-8")).get("decisions", {})
                rotation = d.get("thumbnail_rotation") or {}
                gabarits = {Path(v.get("file", "")).stem: v.get("template")
                            for v in d.get("thumbnail_variants") or []}
        if rotation.get("rotations_done", 0) > 0:
            continue
        suivantes = [(s, gabarits.get(s)) for s in rotation.get("next_variants", [])]
        choix, motif = tv.proposer_rotation(x["ctr_7d"], mediane, suivantes, poids,
                                            seed=zlib.crc32(x["video_id"].encode()))
        sortie.append({"video_id": x["video_id"], "channel_id": x["channel_id"],
                       "ctr_7d": x["ctr_7d"], "ctr_median": mediane, "proposal": choix,
                       "reason": motif})
    return sortie
