"""Ouverture de la base SQLite locale.

Une connexion sqlite3 n'est utilisable que dans le thread qui l'a créée : chaque thread de
travail doit ouvrir la sienne (WAL autorise lecteurs et écrivain concurrents).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=5.0)  # autocommit : transactions explicites
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    return conn
