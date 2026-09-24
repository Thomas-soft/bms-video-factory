"""Chargement de `patterns_<lang>.yaml` — les patrons de hook et les listes de formulations.

Le fichier est une **donnée mesurée**, pas une configuration de goût : les patrons viennent de
l'analyse des 60 vidéos les plus vues du registre (sous-agent A de l'étape 16), les
formulations proscrites de ce que ces mêmes hooks ne font jamais. Le code ne recopie aucune
de ces valeurs.

Production anglaise seulement (décision d'Alek du 15/09/2026) ; le nommage par langue reste
prêt pour l'étape 24, différée. Une langue sans fichier retombe sur l'anglais, comme
`factory/prompts/`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from factory.core.paths import racine_projet

LANGUE_DEFAUT = "en"


@dataclass(frozen=True)
class Patron:
    """Un patron de hook à emplacements, tel que mesuré sur le corpus."""

    texte: str
    element_cle: str
    longueur_mots_mediane: int
    n_observe: int

    @property
    def emplacements(self) -> list[str]:
        """Noms des `{emplacements}` du patron, dans l'ordre d'apparition."""
        return re.findall(r"\{(\w+)\}", self.texte)


@dataclass
class Patterns:
    """Contenu d'un `patterns_<lang>.yaml`, validé à la lecture."""

    langue: str
    patrons: dict[str, list[Patron]] = field(default_factory=dict)
    formulations_proscrites: list[str] = field(default_factory=list)
    marqueurs_plantation: list[str] = field(default_factory=list)
    marqueurs_paiement: list[str] = field(default_factory=list)
    phrases_paiement: list[str] = field(default_factory=list)
    #: Type de hook → nom de l'élément clé que son texte doit porter.
    elements_cles: dict[str, str] = field(default_factory=dict)
    #: Nom d'élément clé → expressions anglaises qui l'attestent.
    lexiques: dict[str, list[str]] = field(default_factory=dict)

    def patron(self, type_hook: str) -> Patron | None:
        """Premier patron du type, ou `None` si le corpus n'en a pas produit."""
        liste = self.patrons.get(type_hook) or []
        return liste[0] if liste else None

    def proscrites_trouvees(self, texte: str) -> list[str]:
        """Formulations proscrites présentes dans `texte`, en clair et dans l'ordre du fichier.

        La comparaison se fait sur un texte normalisé (minuscules, apostrophes typographiques
        ramenées à l'apostrophe droite, espaces resserrés) : le LLM écrit « don’t » aussi
        souvent que « don't », et une liste qui ne voit qu'une des deux ne sert à rien.
        """
        cible = normaliser(texte)
        return [f for f in self.formulations_proscrites if normaliser(f) in cible]

    def plante(self, texte: str) -> list[str]:
        """Marqueurs de plantation de boucle trouvés dans `texte`."""
        return _trouves(self.marqueurs_plantation, texte)

    def paie(self, texte: str) -> list[str]:
        """Marqueurs de paiement de boucle trouvés dans `texte`."""
        return _trouves(self.marqueurs_paiement, texte)


def normaliser(texte: str) -> str:
    """Minuscules, apostrophes droites, espaces resserrés — la forme comparable."""
    plat = texte.lower().replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", plat).strip()


def _trouves(marqueurs: list[str], texte: str) -> list[str]:
    cible = normaliser(texte)
    return [m for m in marqueurs if normaliser(m) in cible]


@lru_cache(maxsize=8)
def charger(lang: str = LANGUE_DEFAUT, racine: Path | None = None) -> Patterns:
    """Lit `factory/retention/patterns_<lang>.yaml`, repli sur l'anglais."""
    dossier = (racine or racine_projet()) / "factory" / "retention"
    chemin = dossier / f"patterns_{lang}.yaml"
    if not chemin.exists():
        chemin = dossier / f"patterns_{LANGUE_DEFAUT}.yaml"
    if not chemin.exists():
        raise FileNotFoundError(f"patrons de rétention absents : {chemin}")
    brut: dict[str, Any] = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}

    patrons: dict[str, list[Patron]] = {}
    for type_hook, entrees in (brut.get("hook_patrons") or {}).items():
        liste = []
        for entree in entrees or []:
            liste.append(Patron(
                texte=str(entree["patron"]),
                element_cle=str(entree.get("element_cle", "")),
                longueur_mots_mediane=int(entree.get("longueur_mots_mediane", 0)),
                n_observe=int(entree.get("n_observe", 0)),
            ))
        patrons[str(type_hook)] = liste

    boucle = brut.get("boucle") or {}
    return Patterns(
        langue=str(brut.get("langue", lang)),
        patrons=patrons,
        formulations_proscrites=[str(f) for f in (brut.get("formulations_proscrites") or [])],
        marqueurs_plantation=[str(m) for m in (boucle.get("marqueurs_plantation") or [])],
        marqueurs_paiement=[str(m) for m in (boucle.get("marqueurs_paiement") or [])],
        phrases_paiement=[str(p) for p in (boucle.get("phrases_paiement") or [])],
        elements_cles={str(k): str(v) for k, v in (brut.get("elements_cles") or {}).items()},
        lexiques={str(k): [str(x) for x in (v or [])]
                  for k, v in (brut.get("lexiques") or {}).items()},
    )
