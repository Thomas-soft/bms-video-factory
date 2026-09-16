#!/usr/bin/env python3
"""Complète a posteriori les mesures TTS écrites avant l'ajout du contrôle de niveau.

Les deux premières synthèses (fr/Ryan, fr/Serena) ont été produites avant que
mesure_niveau() existe. Plutôt que de les refaire — 3 minutes de calcul chacune pour
une donnée que ffmpeg lit en 0,2 s sur le fichier déjà écrit — on complète la ligne.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bench_audio import SAMPLES, mesure_niveau  # noqa: E402

fichier = Path(__file__).parent / "results_audio.jsonl"
lignes = [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l.strip()]
n = 0
for d in lignes:
    if d.get("brique") != "TTS" or "lufs" in d or not d.get("fichier"):
        continue
    wav = SAMPLES / d["fichier"]
    if not wav.exists():
        continue
    d.update(mesure_niveau(wav))
    duree = d.get("duree_audio_s")
    if duree:
        d["mots_par_minute"] = round(d["mots_texte"] / (duree / 60), 1)
    d["complete_a_posteriori"] = True
    n += 1
fichier.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in lignes) + "\n",
                   encoding="utf-8")
print(f"{n} ligne(s) complétée(s)")
