"""Étape 29 — potentiel du réemploi sémantique, rejoué sur des runs passés (simulation).

Pour chaque run illustré : intentions distinctes de `shotlist.json` → meilleure image de la
bibliothèque **produite par un autre run, antérieur** (même préfixe de charte), en cosinus
centré. Compte les intentions au-dessus du seuil : générations qui auraient été évitées.
Ce n'est pas une mesure de production : les runs ont été rendus sans ce réemploi.
"""

import json
import sys

import numpy as np

from factory import library
from factory.core import config, db
from factory.core.paths import racine_projet
from factory.editorial import embed

SEUIL = float(sys.argv[1]) if len(sys.argv) > 1 else 0.9
racine = racine_projet()
conn = db.ouvrir(racine / "workspace" / "factory.db")
cfg = config.charger(racine, strict=False)
mu = library._moyenne(conn)
premiers = {l[0]: (l[1], l[2]) for l in conn.execute(
    "SELECT asset_id, video_id, min(used_at) FROM library_uses GROUP BY asset_id")}

runs = []
for sl in sorted((racine / "workspace/runs").glob("bms-science-*/shotlist.json")):
    vid = sl.parent.name
    m = json.loads((sl.parent / "manifest.json").read_text())
    if m["identite"].get("parent_id"):
        continue
    shots = json.loads(sl.read_text())["shots"]
    intents = sorted({s["asset_request"]["prompt_or_keywords"].strip() for s in shots
                      if s["asset_request"]["type"] != "card"})
    runs.append((vid, m["identite"]["channel_id"], intents))

tous = sorted({i for _, _, ii in runs for i in ii})
vecteurs = dict(zip(tous, embed.embed(tous, racine=racine)))
sortie = []
for vid, cid, intents in runs:
    tag = library.tag_prefixe(cfg.get_channel(cid).charte.style_prefix)
    debut = conn.execute("SELECT min(used_at) FROM library_uses WHERE video_id = ?", (vid,)).fetchone()[0]
    idx = library.IndexSemantique.charger(conn, "images", tag=tag)
    garde = [k for k, a in enumerate(idx.ids)
             if a in premiers and premiers[a][0] != vid and (debut is None or premiers[a][1] < debut)]
    if not garde or not intents:
        sortie.append({"video_id": vid, "intentions": len(intents), "candidats": len(garde),
                       "au_dessus": 0})
        continue
    M = idx.matrice[garde]
    Q = library._centrer(np.vstack([np.asarray(vecteurs[i], np.float32) for i in intents]), mu)
    best = (Q @ M.T).max(axis=1)
    sortie.append({"video_id": vid, "intentions": len(intents), "candidats": len(garde),
                   "au_dessus": int((best > SEUIL).sum()),
                   "mediane": round(float(np.median(best)), 3)})
print(json.dumps(sortie, indent=1))
