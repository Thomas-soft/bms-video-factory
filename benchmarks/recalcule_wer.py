#!/usr/bin/env python3
"""Recalcule le WER des transcriptions déjà produites, brut et hors nombres.

Les transcriptions sont sur disque : recalculer un WER coûte des millisecondes,
là où refaire les seize passes d'ASR coûterait plusieurs minutes de GPU.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from bench_audio import SAMPLES, wer  # noqa: E402

fichier = Path(__file__).parent / "results_audio.jsonl"
lignes = [json.loads(l) for l in fichier.read_text(encoding="utf-8").splitlines() if l.strip()]
for d in lignes:
    if d.get("brique") != "ASR":
        continue
    prefixe = "asr_" if "parakeet" in d["outil"] else "asrw_"
    trans = SAMPLES / f"{prefixe}{Path(d['fichier']).stem}.txt"
    if not trans.exists():
        continue
    ref = (SAMPLES / f"texte_{d['langue']}.txt").read_text(encoding="utf-8")
    hyp = trans.read_text(encoding="utf-8")
    brut, n_ref, _ = wer(ref, hyp)
    net, n_ref_net, _ = wer(ref, hyp, ignorer_nombres=True)
    d["wer"] = round(brut * 100, 2)
    d["wer_hors_nombres"] = round(net * 100, 2)
    d["mots_reference"] = n_ref
    d["mots_reference_hors_nombres"] = n_ref_net
fichier.write_text("\n".join(json.dumps(d, ensure_ascii=False) for d in lignes) + "\n",
                   encoding="utf-8")
print("WER recalculés")
