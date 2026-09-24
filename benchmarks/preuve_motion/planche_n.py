#!/usr/bin/env python3
"""Planche-contact à instants choisis : python3 planche_n.py video.mp4 sortie.png t1 t2 …
Une planche = une image regardée, mais autant d'instants que de temps donnés."""
import subprocess, sys, tempfile, os, math

video, sortie, temps = sys.argv[1], sys.argv[2], [float(t) for t in sys.argv[3:]]
tmp = tempfile.mkdtemp()
for i, t in enumerate(temps):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", video,
                    "-vframes", "1", "-vf", "scale=608:-1", f"{tmp}/f{i}.png"], check=True)
cols = 4
rows = math.ceil(len(temps) / cols)
entrees, filtre, empile = [], "", ""
for i in range(len(temps)):
    entrees += ["-i", f"{tmp}/f{i}.png"]
for r in range(rows):
    idx = [i for i in range(r * cols, min((r + 1) * cols, len(temps)))]
    filtre += "".join(f"[{i}]" for i in idx) + f"hstack={len(idx)}[h{r}];"
    empile += f"[h{r}]"
filtre += empile + f"vstack={rows}[o]" if rows > 1 else "[h0]null[o]"
subprocess.run(["ffmpeg", "-v", "error", "-y", *entrees,
                "-filter_complex", filtre, "-map", "[o]", sortie], check=True)
print(sortie)
