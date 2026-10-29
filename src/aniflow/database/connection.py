"""Ouverture de la base SQLite locale.

Une connexion sqlite3 n'est utilisable que dans le thread qui l'a créée : chaque thread de
travail doit ouvrir la sienne (WAL autorise lecteurs et écrivain concurrents).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: str | Path) -> sqlite3.Connection:
    """Ouvre la base et applique les réglages. Si l'initialisation échoue, la connexion est fermée avant que
    l'erreur ne remonte : une base illisible ne doit jamais laisser son fichier ouvert (sous Windows, un fichier
    ouvert ne peut plus être supprimé ni remplacé, WinError 32).
    """
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=5.0)  # autocommit : transactions explicites
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
    except BaseException:
        # Depuis Python 3.11, une connexion abandonnée n'est libérée que par le ramasse-miettes cyclique (cycle avec
        # son cache d'instructions) : sans fermeture explicite, le fichier reste ouvert un temps indéterminé.
        try:
            conn.close()
        except sqlite3.Error:
            pass  # l'erreur d'origine prime
        raise
    return conn
