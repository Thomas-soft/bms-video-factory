"""Journaux et verrou de la fabrique — la seule trace qui survit à un `kill -9`.

Trois choses, toutes écrites sur disque avant d'être vraies :

1. **`workspace/logs/events.jsonl`** — append-only, une ligne JSON par événement, même
   format de ligne que l'`events.jsonl` d'un run (`ARCHITECTURE` § 7) : `ts`, `job`,
   `video_id`, `stage`, `level`, `msg`, `data`. C'est la preuve de reprise de l'étape 22.1.
2. **`workspace/logs/factory.log`** — lisible par un humain, rotation applicative
   (10 Mo × 5 par défaut). Applicative et non `newsyslog` : une ligne `newsyslog.conf` qui
   omet `owner:group` recrée le fichier en `root:root`, et l'agent utilisateur ne peut
   plus y écrire (veille du 20/09/2026).
3. **`workspace/run.lock`** — un seul run à la fois (`ARCHITECTURE` § 1.4). Un verrou dont
   le PID est **mort** est repris d'office avec un `WARN` : sans cela, le `kill` que teste
   cette étape laisserait un orphelin qui arrête le daemon jusqu'à intervention manuelle.
"""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from factory.core.paths import dossier_workspace

NIVEAUX = ("DEBUG", "INFO", "WARN", "ERROR", "BLOCK")

#: Clés dont la valeur ne doit jamais entrer dans un événement (`ARCHITECTURE` § 1.7).
#: Le filtre porte sur le **nom** de la clé : un événement n'a aucune raison d'en porter.
MOTS_INTERDITS = ("token", "secret", "password", "api_key", "apikey", "client_secret",
                  "refresh_token", "authorization", "bearer")


def maintenant() -> str:
    """Horodatage ISO-8601 UTC à la milliseconde, format d'`INTERFACES` § 0."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def dossier_logs(racine: Path | None = None) -> Path:
    """`workspace/logs/`, créé au besoin."""
    chemin = dossier_workspace(racine) / "logs"
    chemin.mkdir(parents=True, exist_ok=True)
    return chemin


def chemin_events(racine: Path | None = None) -> Path:
    """`workspace/logs/events.jsonl` — le journal de la fabrique, pas celui d'un run."""
    return dossier_logs(racine) / "events.jsonl"


def chemin_factory_log(racine: Path | None = None) -> Path:
    """`workspace/logs/factory.log`."""
    return dossier_logs(racine) / "factory.log"


def _expurger(donnees: dict[str, Any]) -> dict[str, Any]:
    """Retire les clés dont le nom évoque un secret. Rien n'est tronqué silencieusement."""
    propre: dict[str, Any] = {}
    for cle, valeur in donnees.items():
        if any(mot in cle.lower() for mot in MOTS_INTERDITS):
            propre[cle] = "[expurgé]"
        elif isinstance(valeur, dict):
            propre[cle] = _expurger(valeur)
        else:
            propre[cle] = valeur
    return propre


def evenement(
    niveau: str, message: str, *, job: int | None = None, video_id: str | None = None,
    stage: str | None = None, donnees: dict[str, Any] | None = None,
    racine: Path | None = None, conn: sqlite3.Connection | None = None,
) -> dict[str, Any]:
    """Écrit une ligne dans `events.jsonl` (et, si `conn`, dans la table `events`).

    Le fichier fait foi ; la table est un confort de requête qui se reconstruit.
    """
    if niveau not in NIVEAUX:
        raise ValueError(f"niveau inconnu : {niveau} ({', '.join(NIVEAUX)})")
    entree = {
        "ts": maintenant(), "job": job, "video_id": video_id, "stage": stage,
        "level": niveau, "msg": message, "data": _expurger(donnees or {}),
    }
    ligne = json.dumps(entree, ensure_ascii=False)
    with chemin_events(racine).open("a", encoding="utf-8") as flux:
        flux.write(ligne + "\n")
    journaliser(f"{niveau:<5} {message}", racine=racine)
    if conn is not None:
        try:
            conn.execute(
                "INSERT INTO events (ts, job, video_id, stage, level, msg, data) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entree["ts"], job, video_id, stage, niveau, message,
                 json.dumps(entree["data"], ensure_ascii=False)),
            )
        except sqlite3.Error:
            # Le journal ne doit jamais faire tomber un run : le fichier est déjà écrit.
            pass
    return entree


def journaliser(texte: str, racine: Path | None = None,
                taille_max_mo: float = 10.0, fichiers: int = 5) -> None:
    """Une ligne dans `factory.log`, avec rotation **avant** écriture."""
    fichier = chemin_factory_log(racine)
    _tourner(fichier, taille_max_mo, fichiers)
    with fichier.open("a", encoding="utf-8") as flux:
        flux.write(f"{maintenant()} {texte}\n")


def _tourner(fichier: Path, taille_max_mo: float, fichiers: int) -> bool:
    """`factory.log` → `.1` → … → `.N`, le plus ancien étant supprimé. Vrai si tourné."""
    if not fichier.exists() or fichier.stat().st_size < taille_max_mo * 1_000_000:
        return False
    plus_ancien = fichier.with_suffix(fichier.suffix + f".{fichiers}")
    plus_ancien.unlink(missing_ok=True)
    for rang in range(fichiers - 1, 0, -1):
        source = fichier.with_suffix(fichier.suffix + f".{rang}")
        if source.exists():
            source.rename(fichier.with_suffix(fichier.suffix + f".{rang + 1}"))
    fichier.rename(fichier.with_suffix(fichier.suffix + ".1"))
    return True


def lire_events(racine: Path | None = None, depuis: str | None = None) -> list[dict[str, Any]]:
    """Relit `events.jsonl`. Une ligne illisible est ignorée, jamais fatale."""
    fichier = chemin_events(racine)
    if not fichier.exists():
        return []
    lignes: list[dict[str, Any]] = []
    for brut in fichier.read_text(encoding="utf-8").splitlines():
        if not brut.strip():
            continue
        try:
            entree = json.loads(brut)
        except json.JSONDecodeError:
            continue
        if depuis is None or str(entree.get("ts", "")) >= depuis:
            lignes.append(entree)
    return lignes


# --------------------------------------------------------------------------------------
# Verrou d'unicité — un run à la fois
# --------------------------------------------------------------------------------------


class VerrouOccupe(RuntimeError):
    """Le verrou est tenu par un processus **vivant**. Ce n'est pas une attente."""


@dataclass(frozen=True)
class Detenteur:
    """Qui tient le verrou, et depuis quand."""

    pid: int
    hote: str
    quoi: str
    depuis: str

    @property
    def vivant(self) -> bool:
        """Vrai si le PID répond encore. `kill -0` ne tue rien : il teste l'existence."""
        if self.hote != socket.gethostname():
            return True  # un verrou d'une autre machine ne se juge pas d'ici
        try:
            os.kill(self.pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True


def chemin_verrou(racine: Path | None = None, nom: str = "run.lock") -> Path:
    """`workspace/<nom>`."""
    return dossier_workspace(racine) / nom


def detenteur(racine: Path | None = None, nom: str = "run.lock") -> Detenteur | None:
    """Lit le verrou, ou `None` s'il est absent ou illisible."""
    fichier = chemin_verrou(racine, nom)
    if not fichier.exists():
        return None
    try:
        charge = json.loads(fichier.read_text(encoding="utf-8"))
        return Detenteur(int(charge["pid"]), str(charge["hote"]), str(charge.get("quoi", "")),
                         str(charge.get("depuis", "")))
    except (json.JSONDecodeError, KeyError, ValueError, OSError):
        return None


@contextmanager
def verrou_run(quoi: str, racine: Path | None = None, nom: str = "run.lock",
               attendre_s: int = 0) -> Iterator[Path]:
    """Prend `workspace/run.lock` le temps du bloc.

    Tenu par un processus **vivant** : `VerrouOccupe`, pas une attente — deux runs de front
    signalent un défaut de conception et l'attente le masquerait (`ARCHITECTURE` § 1.3).
    Tenu par un PID **mort** : repris d'office, avec un `WARN` au journal.

    `attendre_s > 0` est le régime des **tâches planifiées** (collecte, analytique,
    sauvegarde) : elles sont brèves et différables, elles attendent au lieu d'échouer
    (même § 1.3). Au bout du délai, `VerrouOccupe` est levée et c'est à l'appelant de
    décider — la sauvegarde, elle, passe outre : une sauvegarde manquée coûte plus cher
    qu'une contention de CPU sur 18 Mo.
    """
    fichier = chemin_verrou(racine, nom)
    fichier.parent.mkdir(parents=True, exist_ok=True)
    limite = time.monotonic() + max(attendre_s, 0)
    while attendre_s > 0:
        tenu = detenteur(racine, nom)
        if tenu is None or not tenu.vivant or time.monotonic() >= limite:
            break
        time.sleep(min(5.0, max(0.1, limite - time.monotonic())))
    ancien = detenteur(racine, nom)
    if ancien is not None:
        if ancien.vivant:
            raise VerrouOccupe(
                f"{nom} tenu par le PID {ancien.pid} ({ancien.quoi}) depuis {ancien.depuis} "
                "— un seul run à la fois (ARCHITECTURE § 1.4)"
            )
        evenement("WARN", f"verrou {nom} orphelin repris",
                  donnees={"pid_mort": ancien.pid, "quoi": ancien.quoi,
                           "depuis": ancien.depuis}, racine=racine)
    fichier.write_text(
        json.dumps({"pid": os.getpid(), "hote": socket.gethostname(), "quoi": quoi,
                    "depuis": maintenant()}, ensure_ascii=False),
        encoding="utf-8",
    )
    try:
        yield fichier
    finally:
        # Ne retirer que **notre** verrou : un processus concurrent qui aurait repris un
        # orphelin ne doit pas se le faire effacer par notre sortie.
        courant = detenteur(racine, nom)
        if courant is not None and courant.pid == os.getpid():
            fichier.unlink(missing_ok=True)
