"""Étape 29 — run dérivé de `s57f` pour éprouver l'avatar 2D en incrustation.

Pourquoi un run dérivé : re-rendre `s57f` en place écraserait la vidéo candidate au premier
upload ; un clone sous un nouvel identifiant verrait ses images refusées par le cooldown de la
bibliothèque (10 runs) et en régénérerait une cinquantaine. `heritage.json` (mécanisme de
l'étape 24) sert les images du parent sans génération. Les fichiers sont clonés en copie sur
écriture APFS (`cp -c`) : aucun octet dupliqué tant qu'ils ne sont pas réécrits.

Usage : uv run python benchmarks/etape29_deriver_avatar.py [parent]  → affiche le video_id.
"""

import json
import subprocess
import sys

from factory import run as run_module
from factory.core import config, db, runs
from factory.core.paths import RunPaths, racine_projet
from factory.steps.localize import heritage

PARENT = sys.argv[1] if len(sys.argv) > 1 else "bms-science-en-20260920-s57f"
racine = racine_projet()
parent = RunPaths.depuis_video_id(PARENT, racine)
cfg = config.charger(racine, strict=False)
spec = runs.charger_spec(PARENT, racine)
channel = cfg.get_channel(spec.channel_id)
conn = db.ouvrir(racine / "workspace" / "factory.db")

seed = config.nouvelle_graine()
video_id = config.attribuer_video_id(channel.id, seed, racine=racine, conn=conn)
enfant = RunPaths.depuis_video_id(video_id, racine).creer()

# clones APFS : entrées amont, voix, sous-titres, assets. Ni clips ni calques de texte : le
# gabarit du run enfant (rotation) diffère de celui du parent, tout est recomposé.
for nom in ("research.json", "script.json", "shotlist.json", "words.json", "subtitles.srt",
            "subtitles.ass", "voice", "assets"):
    source = parent.racine / nom
    if source.exists():
        cible = enfant.racine / nom
        if source.is_dir():  # `creer()` a pu créer le dossier : on copie son contenu
            cible.mkdir(exist_ok=True)
            subprocess.run(["cp", "-Rc", f"{source}/.", str(cible)], check=True)
        else:
            subprocess.run(["cp", "-c", str(source), str(cible)], check=True)

for calque in (enfant.racine / "assets").glob("*/overlay.png"):
    calque.unlink()
spec.video_id, spec.parent_id, spec.seed = video_id, PARENT, seed
spec.created_at = runs.maintenant()
runs.ecrire_json(enfant.spec, spec)
(enfant.racine / "heritage.json").write_text(json.dumps(
    heritage(json.loads(parent.shotlist.read_text(encoding="utf-8")), PARENT),
    ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

manifest = runs.charger_manifest(PARENT, racine)
manifest.identite.video_id = video_id
manifest.identite.parent_id = PARENT
manifest.identite.style = "avatar2d"
manifest.identite.template_id = runs.gabarit_suivant(conn, channel.id, list(channel.templates))
manifest.identite.charte_version = channel.charte.version
manifest.children = []
manifest.execution.run_state = "running"
for cle in [k for k in manifest.execution.timings if k.startswith(("render", "assemble", "export"))]:
    del manifest.execution.timings[cle]
runs.ecrire_json(enfant.manifest, manifest)
runs.enregistrer(conn, spec, manifest, racine)
for etape in ("plan", "research", "script", "voice", "subtitles", "shotlist"):
    run_module.marquer(enfant, etape, runs.maintenant(), 0.0, 0)
print(video_id, manifest.identite.template_id)
