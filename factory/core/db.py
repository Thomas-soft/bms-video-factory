"""Base SQLite unique de l'usine : `workspace/factory.db`.

Un seul écrivain, WAL. Les migrations sont des fichiers numérotés de
`factory/core/migrations/` ; chaque étape ajoute les siennes, jamais en modifiant les
précédentes. Les tables de runs sont reconstructibles depuis les `manifest.json`.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from factory.core.paths import chemin_base

DOSSIER_MIGRATIONS = Path(__file__).resolve().parent / "migrations"
MOTIF_MIGRATION = re.compile(r"^(\d{3})_[a-z0-9_]+\.sql$")


def migrations_disponibles() -> list[tuple[int, Path]]:
    """Migrations du dossier, triées par numéro."""
    trouvees: list[tuple[int, Path]] = []
    for fichier in sorted(DOSSIER_MIGRATIONS.glob("*.sql")):
        correspondance = MOTIF_MIGRATION.match(fichier.name)
        if not correspondance:
            raise ValueError(f"migration mal nommée : {fichier.name} (attendu NNN_nom.sql)")
        trouvees.append((int(correspondance.group(1)), fichier))
    return trouvees


def ouvrir(chemin: Path | None = None) -> sqlite3.Connection:
    """Ouvre la base (la crée au besoin), en WAL, et applique les migrations manquantes."""
    fichier = chemin or chemin_base()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(fichier, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    migrer(conn)
    return conn


def migrer(conn: sqlite3.Connection) -> list[int]:
    """Applique les migrations non encore enregistrées. Idempotent. Retourne leurs numéros."""
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version INTEGER PRIMARY KEY, nom TEXT NOT NULL, applied_at TEXT NOT NULL)"
    )
    deja = {ligne["version"] for ligne in conn.execute("SELECT version FROM schema_migrations")}
    appliquees: list[int] = []
    for version, fichier in migrations_disponibles():
        if version in deja:
            continue
        # `executescript` valide toute transaction en cours : la transaction est donc
        # portée par le script lui-même, enregistrement de la migration compris.
        maintenant = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        script = "\n".join(
            [
                "BEGIN;",
                fichier.read_text(encoding="utf-8"),
                "INSERT INTO schema_migrations (version, nom, applied_at) VALUES "
                f"({version}, '{fichier.name}', '{maintenant}');",
                "COMMIT;",
            ]
        )
        conn.executescript(script)
        appliquees.append(version)
    return appliquees


def tables(conn: sqlite3.Connection) -> set[str]:
    """Noms des tables présentes."""
    return {
        ligne["name"]
        for ligne in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def version_schema(conn: sqlite3.Connection) -> int:
    """Numéro de la dernière migration appliquée, 0 si aucune."""
    ligne = conn.execute("SELECT MAX(version) AS v FROM schema_migrations").fetchone()
    return ligne["v"] or 0
