"""Lecture des secrets : `.env` et `secrets/`.

Règle du projet : aucune valeur de secret dans la conversation, les journaux, les manifestes
ni le dépôt. La configuration ne porte que des **références** (`*_ref`), jamais des valeurs.
Ce module ne journalise rien et n'affiche jamais une valeur.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

from dotenv import dotenv_values

from factory.core.paths import racine_projet

#: Noms de variables considérés comme sensibles : jamais recopiés dans un fichier de sortie.
MOTIFS_SENSIBLES = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CLIENT_ID", "CLIENT_SECRET", "REFRESH")


class ErreurSecret(RuntimeError):
    """Secret absent, illisible ou aux permissions trop ouvertes."""


def chemin_env(racine: Path | None = None) -> Path:
    """Chemin du fichier `.env`."""
    return (racine or racine_projet()) / ".env"


def dossier_secrets(racine: Path | None = None) -> Path:
    """Chemin du dossier `secrets/`."""
    return (racine or racine_projet()) / "secrets"


def charger_env(racine: Path | None = None, remplacer: bool = False) -> list[str]:
    """Charge `.env` dans l'environnement. Retourne les **noms** chargés, jamais les valeurs."""
    fichier = chemin_env(racine)
    if not fichier.is_file():
        return []
    valeurs = dotenv_values(fichier)
    charges: list[str] = []
    for nom, valeur in valeurs.items():
        if valeur is None:
            continue
        if remplacer or nom not in os.environ:
            os.environ[nom] = valeur
        charges.append(nom)
    return charges


def est_sensible(nom: str) -> bool:
    """Vrai si le nom de variable désigne un secret."""
    majuscules = nom.upper()
    return any(motif in majuscules for motif in MOTIFS_SENSIBLES)


def masquer(valeur: str | None) -> str:
    """Rend une valeur affichable : sa longueur, jamais son contenu."""
    if not valeur:
        return "(absent)"
    return f"(présent, {len(valeur)} caractères)"


def present(nom: str) -> bool:
    """Vrai si la variable est définie et non vide."""
    return bool(os.environ.get(nom))


def lire(nom: str) -> str:
    """Valeur d'un secret d'environnement. Lève `ErreurSecret` si absent."""
    valeur = os.environ.get(nom)
    if not valeur:
        raise ErreurSecret(
            f"secret {nom} absent : renseigne-le dans .env (ignoré par git, mode 600)"
        )
    return valeur


def permissions_sures(fichier: Path) -> bool:
    """Vrai si le fichier n'est lisible que par son propriétaire (mode 600 ou 400)."""
    if not fichier.exists():
        return False
    mode = stat.S_IMODE(fichier.stat().st_mode)
    return not mode & (stat.S_IRWXG | stat.S_IRWXO)


def chemin_reference(ref: str, racine: Path | None = None) -> Path:
    """Résout une référence `secrets/…` en chemin absolu, sans lire le contenu."""
    if not ref.startswith("secrets/"):
        raise ErreurSecret(f"référence de secret hors de secrets/ : {ref}")
    chemin = (racine or racine_projet()) / ref
    if ".." in Path(ref).parts:
        raise ErreurSecret(f"référence de secret suspecte : {ref}")
    return chemin


def lire_reference_json(ref: str, racine: Path | None = None) -> dict:
    """Charge un fichier de `secrets/` (jeton OAuth, identifiants). Jamais journalisé."""
    chemin = chemin_reference(ref, racine)
    if not chemin.is_file():
        raise ErreurSecret(f"secret introuvable : {ref}")
    if not permissions_sures(chemin):
        raise ErreurSecret(f"permissions trop ouvertes sur {ref} : chmod 600 attendu")
    return json.loads(chemin.read_text(encoding="utf-8"))


def expurger(donnees: dict) -> dict:
    """Copie d'un dictionnaire dont toute valeur sensible est remplacée par un marqueur."""
    return {
        nom: ("***" if est_sensible(str(nom)) and valeur else valeur)
        for nom, valeur in donnees.items()
    }
