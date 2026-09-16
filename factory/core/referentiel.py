"""Lecture de `registre/REFERENTIEL.json` — les cibles chiffrées de l'étape 3.

Le code lit le JSON, jamais une valeur recopiée à la main (décision d'étape 9). Ce module
n'expose que ce dont les étapes 10 et suivantes ont besoin, et ne comble aucun trou :
un champ `a_mesurer` est rendu tel quel, à charge de l'appelant de le signaler.
"""

from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Any

from factory.core.paths import racine_projet


@lru_cache(maxsize=4)
def charger(racine: Path | None = None) -> dict[str, Any]:
    """Contenu de `registre/REFERENTIEL.json`."""
    chemin = (racine or racine_projet()) / "registre" / "REFERENTIEL.json"
    return json.loads(chemin.read_text(encoding="utf-8"))


def niche(nom: str, racine: Path | None = None) -> dict[str, Any]:
    """Bloc d'une niche. Lève `KeyError` avec la liste des niches connues."""
    niches = charger(racine)["niches"]
    if nom not in niches:
        raise KeyError(f"niche inconnue : {nom} (connues : {', '.join(sorted(niches))})")
    return niches[nom]


def taxonomie_hooks(racine: Path | None = None) -> dict[str, dict[str, Any]]:
    """Taxonomie indexée par identifiant de type de hook."""
    return {h["id"]: h for h in charger(racine)["hooks_taxonomie"]}


def types_productibles(racine: Path | None = None) -> set[str]:
    """Types de hook qu'un script peut porter (`intro_chaine_neutre` en est exclu)."""
    return {i for i, h in taxonomie_hooks(racine).items() if h.get("productible", False)}


def tirer_type_hook(nom_niche: str, seed: int, racine: Path | None = None) -> tuple[str, float]:
    """Tire un type de hook selon `hooks.parts` de la niche. Aléa seedé, donc rejouable.

    Renvoie `(type, part)`. Les types non productibles sont retirés avant renormalisation :
    `intro_chaine_neutre` est observé dans le corpus mais ne doit jamais être produit.
    """
    parts: dict[str, float] = dict(niche(nom_niche, racine)["hooks"]["parts"])
    productibles = types_productibles(racine)
    retenus = {t: p for t, p in parts.items() if t in productibles and p > 0}
    if not retenus:
        raise ValueError(f"niche {nom_niche} : aucun type de hook productible dans hooks.parts")
    types = sorted(retenus)
    poids = [retenus[t] for t in types]
    tire = random.Random(seed).choices(types, weights=poids, k=1)[0]
    total = sum(poids)
    return tire, retenus[tire] / total


def sujets_porteurs(nom_niche: str, racine: Path | None = None) -> list[dict[str, Any]]:
    """Sujets porteurs mesurés de la niche, dans l'ordre du référentiel (déjà classés)."""
    return list(niche(nom_niche, racine).get("sujets_porteurs") or [])


def mots_par_minute(nom_niche: str, racine: Path | None = None) -> float:
    """Débit de narration médian de la niche, mesuré sur les transcriptions entières."""
    return float(niche(nom_niche, racine)["mots_par_minute"]["mediane"])


def longueur_hook_max(nom_niche: str, racine: Path | None = None) -> int:
    """Plafond de mots du hook = `hooks.longueur_mots.mediane` de la niche.

    Remplace l'ancien plafond fixe de 35 mots, invalidé par la mesure de l'étape 3
    (18 à 65 mots selon la niche) — décision de Thomas du 15/09/2026.
    """
    return int(round(niche(nom_niche, racine)["hooks"]["longueur_mots"]["mediane"]))


def boucles_minimum(nom_niche: str, racine: Path | None = None) -> int:
    """Nombre minimal de boucles ouvertes imposé par le référentiel (décision, pas mesure)."""
    return int(niche(nom_niche, racine)["hooks"].get("boucles_minimum", 2))


def position_boucle_s(nom_niche: str, racine: Path | None = None) -> float:
    """Position visée de la première boucle ouverte, avec le repli inter-niches mesuré."""
    bloc = niche(nom_niche, racine)["hooks"]["boucle_ouverte"]
    return float(bloc.get("position_s_mediane") or bloc.get("position_s_repli") or 47.9)
