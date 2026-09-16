#!/usr/bin/env python3
"""Contrôles automatiques sur un plan généré — ce que le pHash ne voit pas.

Écrit après l'échec du test des 8 plans du 15/09/2026 : la métrique de palette
avait donné 4/5 à une série dont un plan portait un changement de personnage,
une mèche de cheveux détachée et un pied retourné. Le but ici n'est pas de
prétendre tout attraper, mais de séparer **ce qui est mesurable** de **ce qui
exige un œil**.

C1 — cadrage : le plan est-il encadré (marge uniforme sur les quatre bords) ou
     en pleine page ? Un mélange des deux dans une même vidéo se voit.
C2 — fragments détachés : une petite forme isolée, de la même couleur qu'une
     grande masse voisine, séparée d'elle par quelques pixels de fond. C'est la
     signature d'un morceau qui aurait dû être attaché (mèche, membre, objet).
C3 — palette : écart à la charte de la série (déjà employé, conservé ici).
"""
import json, sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def charge(p, largeur=640):
    im = Image.open(p).convert("RGB")
    h = round(im.height * largeur / im.width)
    return np.asarray(im.resize((largeur, h)), dtype=np.int16)


def c1_cadrage(a, tol=12, marge_min=0.02):
    """Renvoie (encadre, marge_relative). Une marge sur les 4 bords = encadré."""
    h, w, _ = a.shape
    coin = a[0, 0].astype(float)
    def uniforme(bande):
        return np.abs(bande.astype(float) - coin).max() <= tol
    if not (uniforme(a[0]) and uniforme(a[-1]) and uniforme(a[:, 0]) and uniforme(a[:, -1])):
        return False, 0.0                      # le dessin touche un bord
    marges = []
    for bande, n in ((a, h), (a[::-1], h)):
        i = 0
        while i < n and uniforme(bande[i]):
            i += 1
        marges.append(i / n)
    for bande, n in ((a.transpose(1, 0, 2), w), (a.transpose(1, 0, 2)[::-1], w)):
        i = 0
        while i < n and uniforme(bande[i]):
            i += 1
        marges.append(i / n)
    return min(marges) >= marge_min, round(float(min(marges)), 3)


def c2_fragments(a, n_couleurs=6, aire_min=8e-5, aire_max=6e-3, ecart_max=14):
    """Petites formes isolées à quelques pixels d'une grande masse de même teinte."""
    h, w, _ = a.shape
    plat = a.reshape(-1, 3).astype(float)
    # quantification grossière : l'illustration plate a peu de couleurs
    q = (plat // 48).astype(int)
    cles, inv = np.unique(q, axis=0, return_inverse=True)
    inv = inv.reshape(h, w)
    trouves = []
    for c in range(len(cles)):
        masque = inv == c
        if masque.mean() < 1e-3:
            continue
        lab, n = ndimage.label(masque)
        if n < 2:
            continue
        aires = ndimage.sum(masque, lab, range(1, n + 1)) / (h * w)
        grands = [i + 1 for i, ar in enumerate(aires) if ar > aire_max]
        if not grands:
            continue
        masque_grands = np.isin(lab, grands)
        dist = ndimage.distance_transform_edt(~masque_grands)
        for i, ar in enumerate(aires):
            if not (aire_min <= ar <= aire_max):
                continue
            comp = lab == (i + 1)
            d = float(dist[comp].min())
            if 1.5 < d <= ecart_max:
                ys, xs = np.nonzero(comp)
                trouves.append({"aire_pct": round(ar * 100, 3),
                                "ecart_px": round(d, 1),
                                "centre": [int(xs.mean()), int(ys.mean())]})
    return sorted(trouves, key=lambda x: -x["aire_pct"])


def palette(a, bins=(18, 6)):
    im = Image.fromarray(a.astype(np.uint8)).convert("HSV")
    hsv = np.asarray(im, dtype=float)
    hist, _, _ = np.histogram2d(hsv[..., 0].ravel(), hsv[..., 1].ravel(),
                                bins=bins, range=[[0, 256], [0, 256]])
    return hist / hist.sum()


def main(dossier):
    plans = sorted(Path(dossier).glob("plan_*.png"))
    imgs = {p.stem: charge(p) for p in plans}
    pals = {k: palette(v) for k, v in imgs.items()}
    ref = np.median(np.stack(list(pals.values())), axis=0)   # charte de fait

    res = {}
    for k, a in imgs.items():
        enc, marge = c1_cadrage(a)
        frags = c2_fragments(a)
        res[k] = {"encadre": enc, "marge": marge,
                  "fragments_detaches": len(frags),
                  "fragment_principal": frags[0] if frags else None,
                  "palette_vs_serie": round(float(np.minimum(pals[k], ref).sum()), 3)}

    n_enc = sum(1 for v in res.values() if v["encadre"])
    res["_verdict"] = {
        "C1_cadrage": (f"{n_enc} encadré(s) sur {len(imgs)} — "
                       + ("MÉLANGE, la charte ne fixe pas le cadrage"
                          if 0 < n_enc < len(imgs) else "homogène")),
        "C2_fragments": f"{sum(1 for v in res.values() if isinstance(v, dict) and v.get('fragments_detaches'))} plan(s) avec au moins un fragment détaché",
        "C3_palette_min": min(v["palette_vs_serie"] for v in res.values() if "palette_vs_serie" in v),
    }
    print(json.dumps(res, ensure_ascii=False, indent=2))
    Path(dossier, "controles.json").write_text(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "benchmarks/samples/visuel/coherence8")
