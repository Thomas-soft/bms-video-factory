"""Sauvegarde de l'actif : ce qui ne se reconstruit pas, et rien d'autre.

Ce qui entre dans l'archive, et pourquoi c'est exactement cette liste.

* **`workspace/factory.db`**, copié par `sqlite3 .backup` et non par `cp`. Copier un
  fichier SQLite en WAL pendant qu'un run écrit rend une base tronquée qui s'ouvre sans
  broncher et ment. `.backup` prend une copie cohérente, WAL rejoué.
* **Les JSON de chaque run** — `manifest.json`, `metadata.json`, `qc.json`, `publish.json`,
  `spec.json`, `script.json`, `events.jsonl`. C'est **le résidu qui porte la valeur**
  (`ARCHITECTURE` § 8) : ≈ 1,5 Mo par run, l'historique complet tient indéfiniment.
* **`config/`**, **`learned/`**, **`registre/REFERENTIEL.json`**, **`docs/`** — la
  configuration, les poids appris (étape 26, non reconstructibles) et les décisions.
* Ce qui **n'entre pas** : les vidéos (YouTube en garde la copie, et 174 Mo par run
  rendraient la sauvegarde quotidienne impossible), `secrets/` et `.env` (`ARCHITECTURE`
  § 1.7 — une archive de sauvegarde se copie sur un disque externe, un secret non),
  `models/` (21,5 Go de poids re-téléchargeables), `.venv`.

Ce que la sauvegarde ne fait **pas** : sortir de la machine. Une archive à côté de
l'original ne protège que de l'effacement, pas de la perte du Mac. La copier vers un
support externe ou un cloud gratuit est un geste humain, consigné dans
`docs/EXPLOITATION.md`.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Callable

from factory.core.paths import chemin_base, racine_projet
from factory.orchestrator import journal

#: Fichiers d'un run qui entrent dans l'archive. Les vidéos, les clips et les WAV n'y sont
#: pas : ils pèsent mille fois plus et se refabriquent.
FICHIERS_RUN: tuple[str, ...] = (
    "manifest.json", "metadata.json", "qc.json", "publish.json", "spec.json",
    "script.json", "research.json", "shotlist.json", "review.json", "events.jsonl",
    "subtitles.srt", "publication.md",
)

#: Dossiers copiés tels quels, relatifs à la racine du dépôt.
DOSSIERS: tuple[str, ...] = ("config", "learned", "docs")

#: Fichiers isolés copiés tels quels.
FICHIERS: tuple[str, ...] = ("registre/REFERENTIEL.json", "STATE.md", "SUIVI.md", "ROADMAP.md")

#: Jamais dans une archive, quel que soit le chemin qui y mènerait (`ARCHITECTURE` § 1.7).
INTERDITS: tuple[str, ...] = (".env", "secrets", "id_rsa", "client_secret", "token")


@dataclass
class ResultatSauvegarde:
    """Ce qu'a produit `factory backup run`."""

    archive: Path
    octets: int
    fichiers: int
    runs: int
    secondes: float
    supprimees: list[str] = field(default_factory=list)
    compression: str = "gz"

    @property
    def mo(self) -> float:
        """Poids de l'archive, en mégaoctets."""
        return round(self.octets / 1e6, 2)


def destination(racine: Path | None = None) -> Path:
    """Dossier des archives, `~/BMS-backups` par défaut, lu dans `config/orchestrator.yaml`."""
    from factory.orchestrator import runner

    cfg = runner._config(racine)  # noqa: SLF001 — même paquet
    return Path(os.path.expanduser(cfg.sauvegarde.destination))


def _zstd_disponible() -> bool:
    """Vrai si le binaire `zstd` répond. Sinon l'archive est en `.tar.gz`."""
    try:
        return subprocess.run(["zstd", "--version"], capture_output=True, timeout=10,
                              check=False).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _copie_coherente(source: Path, cible: Path) -> None:
    """Copie de la base par `sqlite3 .backup` — jamais un `cp` sur une base en WAL."""
    if not source.exists():
        return
    origine = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
    copie = sqlite3.connect(cible)
    try:
        origine.backup(copie)
    finally:
        copie.close()
        origine.close()


def _interdit(chemin: Path) -> bool:
    """Vrai si un segment du chemin évoque un secret."""
    parties = {p.lower() for p in chemin.parts}
    return any(mot in parties or any(mot in p for p in parties) for mot in INTERDITS)


def _rassembler(racine: Path, atelier: Path) -> tuple[int, int]:
    """Copie dans `atelier` tout ce qui entre dans l'archive. Rend `(fichiers, runs)`."""
    fichiers = 0
    base = atelier / "workspace" / "factory.db"
    base.parent.mkdir(parents=True, exist_ok=True)
    _copie_coherente(chemin_base(racine), base)
    if base.exists():
        fichiers += 1

    runs = 0
    dossier_runs = racine / "workspace" / "runs"
    for dossier in sorted(p for p in dossier_runs.glob("*") if p.is_dir()):
        copies = 0
        for nom in FICHIERS_RUN:
            source = dossier / nom
            if not source.exists() or _interdit(source.relative_to(racine)):
                continue
            cible = atelier / "workspace" / "runs" / dossier.name / nom
            cible.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, cible)
            copies += 1
        fichiers += copies
        runs += 1 if copies else 0

    for nom in DOSSIERS:
        source = racine / nom
        if not source.is_dir():
            continue
        for fichier in sorted(source.rglob("*")):
            if not fichier.is_file() or _interdit(fichier.relative_to(racine)):
                continue
            cible = atelier / fichier.relative_to(racine)
            cible.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(fichier, cible)
            fichiers += 1

    for nom in FICHIERS:
        source = racine / nom
        if not source.is_file() or _interdit(Path(nom)):
            continue
        cible = atelier / nom
        cible.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, cible)
        fichiers += 1

    (atelier / "BACKUP.json").write_text(
        json.dumps({
            "schema_version": "1.0",
            "cree_le": journal.maintenant(),
            "racine": str(racine),
            "contenu": {"runs": runs, "fichiers": fichiers,
                        "dossiers": list(DOSSIERS), "isoles": list(FICHIERS)},
            "exclus": ["secrets/", ".env", "models/", ".venv/", "vidéos et clips"],
            "rappel": "cette archive doit être copiée hors de cette machine "
                      "(docs/EXPLOITATION.md § 4)",
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return fichiers + 1, runs


def executer(racine: Path | None = None,
             echo: Callable[[str], None] | None = None,
             attendre_verrou_s: int = 3600) -> ResultatSauvegarde:
    """`factory backup run` — une archive datée dans `~/BMS-backups`, rétention appliquée."""
    racine = racine or racine_projet()
    dire = echo or (lambda _: None)
    debut = datetime.now(UTC)
    cible = destination(racine)
    cible.mkdir(parents=True, exist_ok=True)

    jour = debut.strftime("%Y%m%d-%H%M")
    zstd = _zstd_disponible()
    archive = cible / (f"factory-{jour}.tar.zst" if zstd else f"factory-{jour}.tar.gz")

    # Tâche planifiée : elle **attend** `run.lock` au lieu d'échouer (`ARCHITECTURE`
    # § 1.3). Si l'attente expire, elle passe outre avec un avertissement — une
    # sauvegarde manquée coûte plus cher qu'une contention de CPU sur 18 Mo.
    try:
        with journal.verrou_run("backup", racine, attendre_s=attendre_verrou_s):
            return _archiver(racine, archive=archive, zstd=zstd, debut=debut, dire=dire)
    except journal.VerrouOccupe as erreur:
        journal.evenement("WARN", f"sauvegarde lancée malgré le verrou : {erreur}",
                          racine=racine)
    return _archiver(racine, archive=archive, zstd=zstd, debut=debut, dire=dire)


def _archiver(racine: Path, *, archive: Path, zstd: bool, debut: datetime,
              dire: Callable[[str], None]) -> ResultatSauvegarde:
    """Rassemble, compresse, applique la rétention. Appelé sous verrou ou non."""
    from factory.orchestrator import runner

    with tempfile.TemporaryDirectory(prefix="bms-backup-") as temporaire:
        atelier = Path(temporaire) / "factory"
        atelier.mkdir(parents=True)
        fichiers, runs = _rassembler(racine, atelier)
        dire(f"{fichiers} fichiers, {runs} runs rassemblés")
        if zstd:
            tar_brut = Path(temporaire) / "factory.tar"
            with tarfile.open(tar_brut, "w") as flux:
                flux.add(atelier, arcname="factory")
            subprocess.run(["zstd", "-19", "-q", "-f", "-o", str(archive), str(tar_brut)],
                           check=True, timeout=1800)
        else:
            with tarfile.open(archive, "w:gz") as flux:
                flux.add(atelier, arcname="factory")

    cfg = runner._config(racine)  # noqa: SLF001
    supprimees = appliquer_retention(archive.parent, cfg.sauvegarde.retention_jours)
    resultat = ResultatSauvegarde(
        archive=archive, octets=archive.stat().st_size, fichiers=fichiers, runs=runs,
        secondes=(datetime.now(UTC) - debut).total_seconds(), supprimees=supprimees,
        compression="zst" if zstd else "gz",
    )
    journal.evenement("INFO", f"sauvegarde écrite : {archive.name} ({resultat.mo} Mo)",
                      donnees={"fichiers": fichiers, "runs": runs,
                               "secondes": round(resultat.secondes, 1),
                               "supprimees": supprimees}, racine=racine)
    return resultat


def appliquer_retention(dossier: Path, jours: int) -> list[str]:
    """Supprime les archives plus vieilles que `jours`. Rend leurs noms."""
    limite = datetime.now(UTC) - timedelta(days=jours)
    supprimees: list[str] = []
    for archive in sorted(dossier.glob("factory-*.tar.*")):
        horodatage = datetime.fromtimestamp(archive.stat().st_mtime, UTC)
        if horodatage < limite:
            archive.unlink()
            supprimees.append(archive.name)
    return supprimees


# --------------------------------------------------------------------------------------
# Test de restauration
# --------------------------------------------------------------------------------------


@dataclass
class ResultatRestauration:
    """Ce qu'a trouvé `factory backup restore-test`."""

    archive: Path
    runs_archive: int
    runs_original: int
    jobs_archive: int
    jobs_original: int
    tables_archive: int
    manifestes: int
    secrets_trouves: list[str]
    secondes: float

    @property
    def ok(self) -> bool:
        """Vrai si la base s'ouvre, que les comptes concordent et qu'aucun secret n'entre."""
        return (self.runs_archive == self.runs_original
                and self.jobs_archive == self.jobs_original
                and self.tables_archive > 0
                and not self.secrets_trouves)


def derniere_archive(racine: Path | None = None) -> Path | None:
    """L'archive la plus récente, ou `None`."""
    cible = destination(racine)
    archives = sorted(cible.glob("factory-*.tar.*"))
    return archives[-1] if archives else None


def tester_restauration(archive: Path | None = None, racine: Path | None = None,
                        echo: Callable[[str], None] | None = None) -> ResultatRestauration:
    """Extrait dans un dossier temporaire, ouvre la base, compte, compare avec l'original."""
    racine = racine or racine_projet()
    dire = echo or (lambda _: None)
    debut = datetime.now(UTC)
    archive = archive or derniere_archive(racine)
    if archive is None:
        raise FileNotFoundError(
            f"aucune archive dans {destination(racine)} — lance `factory backup run`"
        )

    with tempfile.TemporaryDirectory(prefix="bms-restore-") as temporaire:
        atelier = Path(temporaire)
        if archive.suffixes[-1] == ".zst":
            tar_brut = atelier / "factory.tar"
            subprocess.run(["zstd", "-d", "-q", "-f", "-o", str(tar_brut), str(archive)],
                           check=True, timeout=1800)
            source = tar_brut
        else:
            source = archive
        with tarfile.open(source) as flux:
            flux.extractall(atelier, filter="data")
        extrait = atelier / "factory"
        dire(f"extrait dans {extrait}")

        secrets = [str(p.relative_to(extrait)) for p in extrait.rglob("*")
                   if p.is_file() and _interdit(p.relative_to(extrait))]
        base = extrait / "workspace" / "factory.db"
        if not base.exists():
            raise FileNotFoundError(f"{archive.name} ne contient pas workspace/factory.db")
        conn = sqlite3.connect(f"file:{base}?mode=ro", uri=True)
        runs_archive = int(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
        jobs_archive = int(conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
        tables = int(conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
        conn.close()
        manifestes = len(list((extrait / "workspace" / "runs").glob("*/manifest.json")))

    original = sqlite3.connect(f"file:{chemin_base(racine)}?mode=ro", uri=True)
    runs_original = int(original.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
    jobs_original = int(original.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])
    original.close()

    resultat = ResultatRestauration(
        archive=archive, runs_archive=runs_archive, runs_original=runs_original,
        jobs_archive=jobs_archive, jobs_original=jobs_original, tables_archive=tables,
        manifestes=manifestes, secrets_trouves=secrets,
        secondes=(datetime.now(UTC) - debut).total_seconds(),
    )
    journal.evenement("INFO" if resultat.ok else "ERROR",
                      f"test de restauration {'réussi' if resultat.ok else 'ÉCHOUÉ'} : "
                      f"{archive.name}",
                      donnees={"runs": [runs_archive, runs_original],
                               "jobs": [jobs_archive, jobs_original],
                               "tables": tables, "manifestes": manifestes,
                               "secrets": secrets}, racine=racine)
    return resultat
