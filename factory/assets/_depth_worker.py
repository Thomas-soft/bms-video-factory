"""Sous-processus de profondeur : charge Depth Anything V2 Small **une fois**, traite un lot, sort.

Lancé par `factory.assets.parallax`, jamais importé par le pipeline : c'est ce qui garantit qu'à
aucun instant le modèle d'image et le modèle de profondeur ne sont résidents ensemble
(`ARCHITECTURE` § 1.3). Le chargement coûte ~0,5 s et chaque carte ~0,25 s (mesuré étape 5.2) :
payer le chargement une fois par run, et non une fois par plan, est tout l'intérêt du lot.

Entrée : un JSON `{"paires": [[source, destination], …], "modele": "…"}` en argument.
Sortie : une ligne JSON par carte sur stdout, et rien d'autre — l'appelant la lit.
"""

from __future__ import annotations

import json
import sys
import time


def main() -> int:
    tache = json.loads(sys.argv[1])
    modele = tache.get("modele", "depth-anything/Depth-Anything-V2-Small-hf")
    paires = tache["paires"]

    from PIL import Image
    from transformers import pipeline

    depart = time.perf_counter()
    estimateur = pipeline("depth-estimation", model=modele, device="mps")
    chargement = time.perf_counter() - depart

    for source, destination in paires:
        debut = time.perf_counter()
        try:
            carte = estimateur(Image.open(source))["depth"]
            carte.save(destination)
            ligne = {"source": source, "ok": True, "secondes": round(time.perf_counter() - debut, 3)}
        except Exception as erreur:  # une image ratée ne fait pas tomber le lot
            ligne = {"source": source, "ok": False, "erreur": f"{type(erreur).__name__}: {erreur}"}
        ligne["chargement_s"] = round(chargement, 3)
        chargement = 0.0
        print(json.dumps(ligne, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
