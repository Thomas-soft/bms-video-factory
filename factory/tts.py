"""Brique TTS — synthèse vocale locale, dans un sous-processus qui se termine.

`CLAUDE.md` § 4 : un seul modèle IA résident à la fois. Ce module n'est **jamais importé** par
l'étape `voice` ; il est lancé par `python -m factory.tts <travail.json>`, charge le modèle une
seule fois pour tout le run, écrit un WAV par unité, puis meurt en rendant la mémoire.

Modèle retenu à l'étape 5.1 : `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`, float16 / MPS, attention
« eager » (flash-attention n'existe pas sur Metal). Facteur temps réel mesuré 3,29 à 3,57 :
une voix de dix minutes coûte une demi-heure de calcul, machine monopolisée.

Le fichier de travail (JSON) porte : `model`, `language`, `speaker`, `out_dir` et `units`
(liste de `{id, file, text}`). Le compte rendu, ligne par ligne en JSONL sur la sortie standard,
porte pour chaque unité sa durée audio et son temps de calcul.
"""

from __future__ import annotations

import gc
import json
import sys
import time
from pathlib import Path

#: Noms de langue attendus par l'API du modèle, depuis les codes ISO du projet.
LANGUES = {"fr": "French", "en": "English", "es": "Spanish", "it": "Italian"}
#: Dépôt des poids et du tokenizer audio, tous deux Apache-2.0 (`outils/MODELES.md`).
REPO = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
#: Moteurs déclarables par une voix de `config/languages/<code>.yaml` et servis ici.
MOTEURS = {"qwen3_tts"}


def locuteur(voice_id: str) -> str:
    """`serena_fr` → `Serena`. Le suffixe de langue est une convention du projet, pas du modèle."""
    racine = voice_id.rsplit("_", 1)[0] if "_" in voice_id else voice_id
    return racine.replace("_", " ").title()


def main(argv: list[str]) -> int:
    """Charge le modèle une fois, synthétise chaque unité, écrit un JSONL de compte rendu."""
    if len(argv) != 2:
        print("usage : python -m factory.tts <travail.json>", file=sys.stderr)
        return 2
    travail = json.loads(Path(argv[1]).read_text(encoding="utf-8"))

    # HF_HOME doit être posé **avant** l'import de transformers : huggingface_hub le lit à
    # l'import (panne de l'étape 5.1, qui avait fait télécharger whisper deux fois).
    from factory.doctor import charge_env

    charge_env()

    t_charge = time.perf_counter()
    import soundfile as sf
    import torch
    from qwen_tts import Qwen3TTSModel

    modele = Qwen3TTSModel.from_pretrained(
        travail.get("model", REPO), device_map="mps", dtype=torch.float16,
        attn_implementation="eager",
    )
    print(json.dumps({"evenement": "charge", "secondes": round(time.perf_counter() - t_charge, 2)}),
          flush=True)

    langue = travail["language"]
    voix = travail["speaker"]
    for unite in travail["units"]:
        chemin = Path(unite["file"])
        if chemin.exists() and not travail.get("force"):
            print(json.dumps({"evenement": "saute", "id": unite["id"], "fichier": str(chemin)}),
                  flush=True)
            continue
        t0 = time.perf_counter()
        wavs, sr = modele.generate_custom_voice(text=unite["text"], language=langue, speaker=voix)
        calcul = time.perf_counter() - t0
        chemin.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(chemin), wavs[0], sr)
        secondes_audio = len(wavs[0]) / sr
        # Mesuré le 15/09/2026 sur ce run : sans ce nettoyage, le cache d'allocations MPS
        # grossit d'unité en unité et la machine se met à comprimer de la mémoire — le temps
        # *entre* deux synthèses passait de 0 à 250-425 s après la dixième, pour un temps de
        # calcul inchangé (facteur temps réel toujours à 3,3). Le libérer est gratuit.
        t_libere = time.perf_counter()
        del wavs
        gc.collect()
        if hasattr(torch, "mps"):
            torch.mps.empty_cache()
        print(json.dumps({
            "evenement": "unite", "id": unite["id"], "fichier": str(chemin),
            "duree_audio_s": round(secondes_audio, 3), "temps_s": round(calcul, 2),
            "rtf": round(calcul / secondes_audio, 3) if secondes_audio else None,
            "liberation_s": round(time.perf_counter() - t_libere, 2),
            "sample_rate": sr, "mots": len(unite["text"].split()),
        }), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
