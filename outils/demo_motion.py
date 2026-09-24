"""Rend un **extrait court** d'un run en style motion design, voix comprise.

    uv run --python .venv/bin/python outils/demo_motion.py <run_id> <premier> <dernier>

Sert à juger le moteur sans rendre dix minutes de vidéo : Thomas, 19/09/2026 — « pour les tests
faudrait que tu fasses quelques courtes vidéos de demo, pas une video complete, car si je commence
à te faire recommencer des videos de 10min plusieurs fois on va jamais s'en sortir ».

L'extrait est construit exactement comme un run : mêmes spécifications, même rendu par lots, même
découpe. Seule la liste de plans est tronquée. La voix est la tranche correspondante de
`voice/voice.wav`, pour que le rythme des apparitions se juge avec le son.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

from factory import video
from factory.core import config as config_module
from factory.core.models import Shotlist
from factory.core.paths import RunPaths, racine_projet
from factory.styles import get_engine

SORTIE = Path("workspace/logs/etape30_1")


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    video_id, premier, dernier = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    racine = racine_projet()
    source = RunPaths.depuis_video_id(video_id, racine)
    shotlist = Shotlist.model_validate_json(source.shotlist.read_text(encoding="utf-8"))
    plans = shotlist.shots[premier:dernier]
    if not plans:
        print(f"aucun plan entre {premier} et {dernier}")
        return 2

    # Un run jetable : mêmes entrées, plans tronqués, sorties à part.
    demo_id = f"{video_id}-demo{premier}"
    base = racine / "workspace" / "demos" / demo_id
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    for nom in ("script.json", "words.json", "spec.json", "manifest.json"):
        shutil.copy2(source.racine / nom, base / nom)
    tronque = shotlist.model_copy(update={"shots": plans})
    (base / "shotlist.json").write_text(
        tronque.model_dump_json(indent=1) + "\n", encoding="utf-8"
    )
    demo = RunPaths(video_id=demo_id, racine=base)

    cfg = config_module.charger(racine, strict=False)
    spec = json.loads(source.spec.read_text(encoding="utf-8"))
    channel = cfg.get_channel(spec["channel_id"])
    journal = racine / "workspace" / "logs" / "etape30_1_demo_moteur.log"
    with journal.open("a", encoding="utf-8") as trace:
        trace.write(f"\n===== demo {demo_id} plans {premier}-{dernier} =====\n")
        moteur = get_engine(cfg.styles["motion"], racine, journal=trace)
        langue = cfg.languages.get(channel.lang)
        moteur.texte_divulgation = langue.disclosure.overlay_generic if langue else None
        t0 = time.perf_counter()
        moteur.prepare_assets(tronque, channel, demo)
        secondes = time.perf_counter() - t0

    # Assemblage minimal : coupe franche entre les plans, plus la tranche de voix qui va avec.
    liste = base / "clips.txt"
    liste.write_text(
        "".join(f"file '{demo.clip(p.id).resolve()}'\n" for p in plans), encoding="utf-8"
    )
    muet = base / "muet.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(liste),
         "-c", "copy", str(muet)], check=True,
    )
    SORTIE.mkdir(parents=True, exist_ok=True)
    sortie = SORTIE / f"demo_{demo_id}.mp4"
    debut = plans[0].start_s
    duree = sum(p.duration_s for p in plans)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(muet),
         "-ss", f"{debut:.3f}", "-t", f"{duree:.3f}", "-i", str(source.voice_wav),
         "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-shortest", str(sortie)], check=True,
    )

    compte: dict[str, int] = {}
    for lot in json.loads(
        (racine / "render" / "specs" / demo_id / "batch.json").read_text(encoding="utf-8")
    )["lots"]:
        for plan in lot["shots"]:
            compte[plan["scene"]] = compte.get(plan["scene"], 0) + 1
    print(f"{len(plans)} plans · {duree:.1f} s · rendu en {secondes:.1f} s")
    print("scènes : " + " · ".join(f"{k} {v}" for k, v in sorted(compte.items())))
    print(f"écrit : {sortie}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
