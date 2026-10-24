"""Ouverture de la base de l'application : dossiers, connexion, migrations (avec sauvegarde préalable)."""

from __future__ import annotations

import sqlite3

from aniflow.paths import AppPaths

from .connection import connect
from .migrations import migrate


def open_app_database(paths: AppPaths | None = None) -> sqlite3.Connection:
    paths = (paths or AppPaths.default()).ensure()
    conn = connect(paths.database)
    try:
        migrate(conn, backups_dir=paths.backups)
    except BaseException:
        conn.close()
        raise
    return conn
