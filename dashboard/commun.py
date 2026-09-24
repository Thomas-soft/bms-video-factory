"""Socle partagé des pages : langue, base, commandes en arrière-plan, YAML de chaîne.

Aucune logique métier ici : les décisions (relecture, file, sujets, validation) restent dans
`factory`. Ce module ne fait que traduire, ouvrir, lancer et afficher.
"""

from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from factory.core import db
from factory.core.paths import racine_projet

DOSSIER = Path(__file__).resolve().parent
LANGUES = ("fr", "en")

# --------------------------------------------------------------------------------------
# Langue
# --------------------------------------------------------------------------------------


@st.cache_data
def _textes(langue: str) -> dict[str, str]:
    return yaml.safe_load((DOSSIER / "i18n" / f"{langue}.yaml").read_text(encoding="utf-8"))


def langue() -> str:
    return st.session_state.get("langue", "fr")


def t(cle: str, **valeurs: Any) -> str:
    """Texte traduit ; la clé brute si elle manque, pour qu'un oubli se voie."""
    texte = _textes(langue()).get(cle) or _textes("fr").get(cle) or cle
    return texte.format(**valeurs) if valeurs else texte


def entete(cle_titre: str) -> None:
    """Sélecteur de langue et titre de page — appelé en tête de chaque page."""
    st.session_state.setdefault("langue", "fr")
    st.sidebar.radio("Langue / Language", LANGUES, key="langue", horizontal=True,
                     format_func=lambda c: {"fr": "Français", "en": "English"}[c])
    st.title(t(cle_titre))


# --------------------------------------------------------------------------------------
# Base et chemins
# --------------------------------------------------------------------------------------


def racine() -> Path:
    return racine_projet()


def base():
    """Connexion à `workspace/factory.db`, migrations comprises (même porte que la CLI)."""
    return db.ouvrir(racine() / "workspace" / "factory.db")


def lignes(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    conn = base()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def chaines() -> list[str]:
    return sorted(p.stem for p in (racine() / "config" / "channels").glob("*.yaml"))


def ouvrir_localement(chemin: Path) -> None:
    """Ouvre un fichier avec l'application par défaut de macOS (lecteur vidéo, Aperçu)."""
    subprocess.Popen(["open", str(chemin)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# --------------------------------------------------------------------------------------
# Commandes `factory` en arrière-plan
# --------------------------------------------------------------------------------------


def _dossier_taches() -> Path:
    dossier = racine() / "workspace" / "logs" / "dashboard"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def _vivant(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ValueError):
        return False
    return True


def etat_tache(nom: str) -> tuple[bool, str]:
    """`(en cours ?, fin du journal)` d'une commande lancée depuis le tableau de bord."""
    dossier = _dossier_taches()
    pid_f, log_f = dossier / f"{nom}.pid", dossier / f"{nom}.log"
    en_cours = pid_f.exists() and _vivant(int(pid_f.read_text() or 0))
    fin = ""
    if log_f.exists():
        fin = "\n".join(log_f.read_text(encoding="utf-8", errors="replace").splitlines()[-15:])
    return en_cours, masquer(fin)


def lancer(nom: str, arguments: list[str]) -> bool:
    """Lance `factory <arguments>` détaché, sortie dans `workspace/logs/dashboard/<nom>.log`.

    Refuse un second lancement tant que le premier tourne (un seul run lourd à la fois).
    """
    if etat_tache(nom)[0]:
        return False
    dossier = _dossier_taches()
    with (dossier / f"{nom}.log").open("w", encoding="utf-8") as sortie:
        proc = subprocess.Popen(
            [sys.executable, "-m", "factory.cli", *arguments], cwd=racine(),
            stdout=sortie, stderr=subprocess.STDOUT, start_new_session=True,
            env={**os.environ, "FACTORY_ROOT": str(racine()), "NO_COLOR": "1"},
        )
    (dossier / f"{nom}.pid").write_text(str(proc.pid))
    return True


def arreter_tache(nom: str) -> None:
    pid_f = _dossier_taches() / f"{nom}.pid"
    if pid_f.exists() and _vivant(int(pid_f.read_text() or 0)):
        os.killpg(int(pid_f.read_text()), signal.SIGTERM)


def bouton_tache(nom: str, arguments: list[str], cle_libelle: str) -> None:
    """Bouton + état rafraîchi toutes les 5 s tant que la commande tourne."""
    if st.button(t(cle_libelle), key=f"lancer_{nom}"):
        if lancer(nom, arguments):
            st.toast(t("tache_lancee", commande="factory " + " ".join(arguments)))
        else:
            st.warning(t("tache_deja"))

    @st.fragment(run_every=5)
    def _etat() -> None:
        en_cours, fin = etat_tache(nom)
        if en_cours:
            st.info(t("tache_en_cours"))
        if fin:
            with st.expander(t("tache_journal"), expanded=en_cours):
                st.code(fin, language=None)

    _etat()


# --------------------------------------------------------------------------------------
# Secrets : jamais affichés
# --------------------------------------------------------------------------------------

_SECRET = re.compile(
    r"(?i)((?:token|secret|password|api[_-]?key|client_secret|bearer)[\"'\s:=]+)([^\s\"',]{6,})")


def masquer(texte: str) -> str:
    """Remplace toute valeur qui suit un mot de secret par `***`."""
    return _SECRET.sub(r"\1***", texte)


# --------------------------------------------------------------------------------------
# YAML de chaîne : on remplace une valeur sur sa ligne, le reste du fichier ne bouge pas
# --------------------------------------------------------------------------------------


def _scalaire(valeur: Any, guillemets: bool = False) -> str:
    if valeur is None:
        return "null"
    if isinstance(valeur, bool):
        return "true" if valeur else "false"
    if isinstance(valeur, (int, float)):
        return str(valeur)
    texte = str(valeur)
    if guillemets or not re.fullmatch(r"[A-Za-z0-9_.\-/]+", texte) or texte in ("null", "true", "false"):
        return json.dumps(texte, ensure_ascii=False)
    return texte


def rendre_yaml(valeur: Any, guillemets: bool = False) -> str:
    """Une valeur sur une ligne : scalaire, ou liste en style « flow »."""
    if isinstance(valeur, list):
        return "[" + ", ".join(_scalaire(v, guillemets) for v in valeur) + "]"
    return _scalaire(valeur, guillemets)


def remplacer_valeur(texte: str, section: str | None, cle: str, valeur: Any,
                     guillemets: bool = False) -> str:
    """Remplace la valeur de `section.cle` (ou `cle` au premier niveau) sur sa ligne.

    Le commentaire de fin de ligne est gardé. Les heures « 17:00 » passent `guillemets` :
    sans eux, YAML 1.1 les lit comme un entier sexagésimal. Lève `KeyError` si la clé
    n'est pas une ligne simple du fichier.
    """
    lignes = texte.splitlines(keepends=True)
    dans = section is None
    retrait = "  " if section else ""
    motif = re.compile(rf"^{retrait}{re.escape(cle)}:(?P<esp>[ \t]*)(?P<val>[^#\n]*?)"
                       r"(?P<com>[ \t]+#.*)?(?P<fin>\r?\n?)$")
    for i, ligne in enumerate(lignes):
        if section is not None and not ligne.startswith((" ", "#", "\n")):
            dans = ligne.startswith(f"{section}:")
            continue
        if not dans:
            continue
        m = motif.match(ligne)
        if m:
            rendu = rendre_yaml(valeur, guillemets)
            com = m["com"] or ""
            if com:
                # Garde la colonne du commentaire quand la nouvelle valeur le permet.
                largeur = len(m["val"]) + len(com) - len(com.lstrip())
                com = " " * max(1, largeur - len(rendu)) + com.lstrip()
            lignes[i] = f"{retrait}{cle}:{m['esp'] or ' '}{rendu}{com}{m['fin']}"
            return "".join(lignes)
    raise KeyError(f"{section + '.' if section else ''}{cle}")


def enregistrer_config(genre: str, identifiant: str, texte: str) -> list[Any]:
    """Valide `texte` comme `config/<genre>/<identifiant>.yaml`, puis l'écrit.

    Même contrôle que `factory config validate --file` (`config.valider_fichier`), sur une
    copie hors de `config/` ; rien n'est écrit s'il reste une erreur. L'ancien fichier est
    gardé en `<identifiant>.yaml.bak`. Rend les problèmes (erreurs et avertissements).
    """
    import tempfile

    from factory.core import config as config_module

    with tempfile.TemporaryDirectory() as atelier:
        candidat = Path(atelier) / genre / f"{identifiant}.yaml"
        candidat.parent.mkdir()
        candidat.write_text(texte, encoding="utf-8")
        problemes = config_module.valider_fichier(candidat, genre)
    if any(p.niveau == "erreur" for p in problemes):
        return problemes
    cible = racine() / "config" / genre / f"{identifiant}.yaml"
    if cible.exists():
        cible.with_name(cible.name + ".bak").write_bytes(cible.read_bytes())
    cible.write_text(texte, encoding="utf-8")
    return problemes
