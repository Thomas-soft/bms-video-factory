"""Lecture de `learned/weights.json` (étape 26) par les modules qui décident.

Un seul point d'entrée pour tous les consommateurs : le fichier est lu s'il existe **et** si sa
version majeure est compatible ; sinon `None`, et chaque consommateur retombe sur le
référentiel. Un fichier illisible ne fait jamais tomber une production.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

CHEMIN = Path("learned") / "weights.json"
#: Version du format écrite par `learn.py`. Les consommateurs acceptent la même majeure.
VERSION = "1.0"
MULT_MIN, MULT_MAX = 0.7, 1.4


def compatible(version: Any) -> bool:
    return isinstance(version, str) and version.split(".")[0] == VERSION.split(".")[0]


def charger(racine: Path | None) -> dict[str, Any] | None:
    """Contenu de weights.json, ou `None` (absent, illisible, version incompatible)."""
    if racine is None:
        return None
    fichier = racine / CHEMIN
    if not fichier.is_file():
        return None
    try:
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(donnees, dict) or not compatible(donnees.get("version")):
        return None
    return donnees


def etiquette(poids: dict[str, Any] | None) -> str | None:
    """« 1.0@2026-09-23 » pour le manifeste, ou `None` si aucun poids n'est lu."""
    if not poids:
        return None
    return f"{poids.get('version')}@{str(poids.get('generated_at', ''))[:10]}"


def borne(valeur: Any) -> float:
    """Multiplicateur fini, borné à [0,7 ; 1,4] ; 1,0 pour tout ce qui n'est pas un nombre."""
    try:
        v = float(valeur)
    except (TypeError, ValueError):
        return 1.0
    if not math.isfinite(v) or v <= 0:
        return 1.0
    return min(MULT_MAX, max(MULT_MIN, v))


def multiplicateur(poids: dict[str, Any] | None, facteur: str, niveau: Any) -> float:
    """Multiplicateur d'un niveau de facteur ; 1,0 si absent, gelé ou inactif."""
    if not poids or niveau is None:
        return 1.0
    f = (poids.get("factors") or {}).get(facteur) or {}
    if f.get("frozen"):
        return 1.0
    niv = (f.get("levels") or {}).get(str(niveau)) or {}
    if not niv.get("active"):
        return 1.0
    return borne(niv.get("multiplier"))


def noter(manifest: Any, poids: dict[str, Any] | None, cle: str, valeur: Any) -> None:
    """Journalise au manifeste la version lue et le poids appliqué pour `cle`."""
    decisions = manifest.decisions
    decisions.learned_version = etiquette(poids)
    if poids is not None:
        decisions.learned_applied = {**(decisions.learned_applied or {}), cle: valeur}
