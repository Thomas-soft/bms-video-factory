#!/usr/bin/env python3
"""Cohérence de style sur 8 plans consécutifs d'une même vidéo — étape 5.2.

Le seuil de `outils/SELECTION.md` § 4 dit : « Thomas juge ≥ 4/5 les 8 plans comme
appartenant à la même vidéo. » L'étape 5.2 avait produit 5 styles *différents*,
ce qui ne mesure pas cela. Ici : un seul script, une seule charte, 8 intentions
visuelles consécutives, et une graine par plan — exactement ce que fera
`factory/assets/images.py` à l'étape 12.2 (`graine = hash(video_id, plan)`).

Attention à l'instrument : le pHash compare des *structures*. Entre 8 plans de
contenus différents il sera grand par construction, et ce n'est pas un défaut de
style. La cohérence de style se lit dans la **palette** et dans les **statistiques
globales** — c'est ce qui saute aux yeux quand un plan « ne va pas avec les
autres ». Les deux sont mesurés, et le pHash sert de témoin de contraste.
"""
import hashlib, itertools, json, statistics, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "benchmarks" / "samples" / "visuel" / "coherence8"
MFLUX = Path.home() / ".local/bin/mflux-generate-flux2"
MODEL = "mlx-community/FLUX.2-Klein-4B-4bit"
VIDEO_ID = "bms-demo-sommeil"

# La charte de chaîne : préfixe + suffixe encadrent chaque intention visuelle.
# C'est la forme que prendra `charte.style_prefix` / `style_suffix` en 12.2.
PREFIXE = ("flat vector illustration, bold clean outlines, limited palette of "
           "deep navy blue, warm orange and cream, soft paper grain, "
           "simple geometric shapes, ")
SUFFIXE = ", no text, no lettering, centered composition, 16:9, calm mood"

# Huit plans consécutifs d'un même script de vulgarisation sur le sommeil.
PLANS = [
    "a person lying awake in bed at night, eyes open, moonlight through the window",
    "a human brain seen from the side with three glowing zones",
    "a bedside alarm clock showing the middle of the night",
    "an abstract chart of sleep cycles as smooth repeating waves",
    "a person sleeping peacefully curled under a blanket",
    "a cup of coffee steaming on a wooden desk beside a notebook",
    "a bedroom with heavy curtains drawn, warm dim lamp light",
    "a person walking outdoors in early morning light, stretching",
]


def genere():
    OUT.mkdir(parents=True, exist_ok=True)
    temps = []
    for i, intention in enumerate(PLANS, start=1):
        dest = OUT / f"plan_{i:02d}.png"
        # `hash()` est randomisé par processus (PYTHONHASHSEED) : deux runs
        # donneraient deux graines. Il faut un hachage stable, sinon la
        # reproductibilité d'un plan est perdue — piège à ne pas hériter en 12.2.
        graine = int(hashlib.sha256(f"{VIDEO_ID}:{i}".encode()).hexdigest()[:8], 16) % 100000
        if dest.exists():
            continue
        t = time.time()
        r = subprocess.run([str(MFLUX), "--model", MODEL,
                            "--prompt", PREFIXE + intention + SUFFIXE,
                            "--width", "1280", "--height", "720", "--steps", "4",
                            "--seed", str(graine), "--low-ram", "--vae-tiling",
                            "--output", str(dest)], capture_output=True, text=True)
        secs = time.time() - t
        temps.append(secs)
        print(f"plan {i}/8 : {secs:.0f}s graine={graine} ok={dest.exists()}", flush=True)
        if not dest.exists():
            print((r.stdout + r.stderr)[-400:], flush=True)
            sys.exit(1)
    return temps


def mesure():
    import imagehash
    import numpy as np
    from PIL import Image

    plans = sorted(OUT.glob("plan_*.png"))
    phash, palette, stats = {}, {}, {}
    for p in plans:
        im = Image.open(p).convert("RGB")
        phash[p.stem] = imagehash.phash(im)
        # Palette : histogramme teinte x saturation, normalisé. Insensible au
        # sujet, sensible au traitement chromatique — donc au style.
        hsv = np.asarray(im.convert("HSV").resize((256, 144)), dtype=float)
        h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
        hist, _, _ = np.histogram2d(h.ravel(), s.ravel(), bins=(18, 6),
                                    range=[[0, 256], [0, 256]])
        palette[p.stem] = hist / hist.sum()
        stats[p.stem] = {"luminance": float(v.mean()),
                         "saturation": float(s.mean()),
                         "contraste": float(v.std())}

    def inter(a, b):        # intersection d'histogrammes : 1 = palettes identiques
        return float(np.minimum(palette[a], palette[b]).sum())

    paires = list(itertools.combinations(sorted(phash), 2))
    d_pal = {f"{a}|{b}": round(inter(a, b), 3) for a, b in paires}
    d_pha = {f"{a}|{b}": int(phash[a] - phash[b]) for a, b in paires}

    res = {
        "video_id": VIDEO_ID, "plans": len(plans),
        "palette_intersection": {
            "mediane": round(statistics.median(d_pal.values()), 3),
            "min": min(d_pal.values()), "max": max(d_pal.values()),
            "paire_la_plus_eloignee": min(d_pal, key=d_pal.get)},
        "phash_temoin": {
            "mediane": statistics.median(d_pha.values()),
            "min": min(d_pha.values()), "max": max(d_pha.values())},
        "statistiques_globales": {
            k: {"mediane": round(statistics.median(x[k] for x in stats.values()), 1),
                "etendue": round(max(x[k] for x in stats.values())
                                 - min(x[k] for x in stats.values()), 1)}
            for k in ("luminance", "saturation", "contraste")},
        "par_plan": {k: {a: round(b, 1) for a, b in v.items()} for k, v in stats.items()},
    }
    (OUT / "mesures.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))
    print(json.dumps(res, ensure_ascii=False, indent=2), flush=True)
    return res


if __name__ == "__main__":
    if "--mesure-seule" not in sys.argv:
        t = genere()
        if t:
            print(f"génération : médiane {statistics.median(t):.0f}s, "
                  f"total {sum(t)/60:.1f} min", flush=True)
    mesure()
