"""Étape 29 — données de `reports/compound.md`, lues dans les manifestes et la base.

Aucune estimation : chaque colonne vient d'un champ de `manifest.json` ou de `library_uses`.
Sortie : JSON sur stdout (une ligne par run, ordre de création).
"""

import json

from factory import library
from factory.core import db
from factory.core.paths import racine_projet

racine = racine_projet()
conn = db.ouvrir(racine / "workspace" / "factory.db")
lignes = []
for manifeste in sorted((racine / "workspace" / "runs").glob("*/manifest.json")):
    m = json.loads(manifeste.read_text(encoding="utf-8"))
    spec_f = manifeste.parent / "spec.json"
    spec = json.loads(spec_f.read_text(encoding="utf-8")) if spec_f.exists() else {}
    e, d, i = m.get("execution", {}), m.get("decisions", {}), m.get("identite", {})
    t = e.get("timings", {})
    reuse = d.get("library_reuse") or {}
    vid = i.get("video_id") or manifeste.parent.name
    croise = library.taux_reemploi(conn, [vid])
    sem = conn.execute("SELECT count(*) FROM library_semantic_reuse WHERE video_id = ?",
                       (vid,)).fetchone()[0]
    lignes.append({
        "video_id": vid, "created_at": spec.get("created_at") or e.get("run_started_at"),
        "channel": i.get("channel_id"), "style": i.get("style"), "parent": i.get("parent_id"),
        "template": i.get("template_id"), "charte": i.get("charte_version"),
        "state": e.get("run_state"), "qc": d.get("qc_verdict"),
        "compute_min": (e.get("cost") or {}).get("compute_min"),
        "eur": (e.get("cost") or {}).get("eur"),
        "render_s": t.get("render"), "render_assets_s": t.get("render_assets"),
        "voice_s": t.get("voice"), "script_s": t.get("script"),
        "images_generees": reuse.get("assets_generated"),
        "images_reprises": reuse.get("assets_reused"), "reuse_ratio": reuse.get("reuse_ratio"),
        "emplois": croise["emplois"], "reemplois_inter_runs": croise["reemplois"],
        "reemplois_semantiques": sem, "duree_s": d.get("duration_s"),
    })
lignes.sort(key=lambda l: l["created_at"] or "")
print(json.dumps(lignes, ensure_ascii=False, indent=1))
