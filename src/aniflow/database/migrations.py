"""Migrations de schéma versionnées (PRAGMA user_version), atomiques et précédées d'une sauvegarde."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from .backup import backup_database
from .errors import DatabaseTooNewError, MigrationError


@dataclass(frozen=True)
class Migration:
    version: int
    description: str
    sql: str  # sans BEGIN/COMMIT ni PRAGMA user_version : ajoutés par migrate()


_V1_FOUNDATION = """
CREATE TABLE settings (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,   -- JSON
    updated_at TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE http_cache (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,   -- JSON
    expires_at REAL NOT NULL
) WITHOUT ROWID;
CREATE INDEX idx_http_cache_expires ON http_cache(expires_at);
"""

MIGRATIONS: tuple[Migration, ...] = (Migration(1, "Fondations : paramètres et cache HTTP", _V1_FOUNDATION),)
LATEST_VERSION = MIGRATIONS[-1].version


def current_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


def migrate(conn: sqlite3.Connection, *, backups_dir: Path | None = None, migrations: Sequence[Migration] = MIGRATIONS) -> list[int]:
    """Applique les migrations en attente et retourne les versions appliquées."""
    versions = [m.version for m in migrations]
    if versions != list(range(1, len(versions) + 1)):
        raise ValueError("les migrations doivent être numérotées 1, 2, 3… sans trou")
    latest = versions[-1]
    current = current_version(conn)
    if current > latest:
        raise DatabaseTooNewError(current, latest)
    pending = [m for m in migrations if m.version > current]
    if not pending:
        return []
    if current > 0 and backups_dir is not None:
        backup_database(conn, backups_dir, tag=f"pre-migration-v{current}")
    applied: list[int] = []
    for migration in pending:
        script = f"BEGIN IMMEDIATE;\n{migration.sql}\nPRAGMA user_version = {int(migration.version)};\nCOMMIT;"
        try:
            conn.executescript(script)
        except sqlite3.Error as exc:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise MigrationError(migration.version, str(exc)) from exc
        applied.append(migration.version)
    return applied
