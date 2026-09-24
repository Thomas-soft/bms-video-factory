#!/usr/bin/env python3
"""Lance un rendu Revideo et échantillonne la mémoire de tout l'arbre de processus.

Sortie : un JSON sur stdout (dernière ligne) — secondes de calcul, pic RSS cumulé.
Le pic est la somme des RSS du node de rendu et de toute sa descendance (Chromium,
ffmpeg), échantillonnée toutes les 0,4 s. Ce n'est pas la mémoire système : c'est ce
que le rendu occupe."""
import json, subprocess, sys, time, os, collections

projet, sortie, journal = sys.argv[1], sys.argv[2], sys.argv[3]

# Revideo tourne sur le Chromium DÉJÀ présent pour Playwright : mesuré équivalent
# (8,05 s contre 8,31 s sur la séquence B) et cela évite 0,59 Go de navigateur en double.
env = dict(os.environ)
env["PUPPETEER_EXECUTABLE_PATH"] = os.path.abspath(
    "../../../models/playwright/chromium_headless_shell-1234/"
    "chrome-headless-shell-mac-arm64/chrome-headless-shell")
env["DISABLE_TELEMETRY"] = "true"

with open(journal, "w") as jl:
    t0 = time.time()
    p = subprocess.Popen(["node", "render.mjs", projet, sortie],
                         stdout=jl, stderr=subprocess.STDOUT, env=env)
    pic = 0
    n = 0
    while p.poll() is None:
        try:
            ps = subprocess.run(["ps", "-axo", "pid=,ppid=,rss="],
                                capture_output=True, text=True, timeout=5).stdout
            enfants = collections.defaultdict(list)
            rss = {}
            for ligne in ps.splitlines():
                c = ligne.split()
                if len(c) < 3:
                    continue
                pid, ppid, r = int(c[0]), int(c[1]), int(c[2])
                enfants[ppid].append(pid)
                rss[pid] = r
            total, pile = 0, [p.pid]
            vus = set()
            while pile:
                q = pile.pop()
                if q in vus:
                    continue
                vus.add(q)
                total += rss.get(q, 0)
                pile.extend(enfants.get(q, []))
            pic = max(pic, total)
            n += 1
        except Exception:
            pass
        time.sleep(0.4)
    code = p.wait()
    duree = time.time() - t0

print(json.dumps({"projet": projet, "sortie": sortie, "code": code,
                  "secondes": round(duree, 2), "pic_rss_go": round(pic / 1024 / 1024, 2),
                  "echantillons": n}, ensure_ascii=False))
