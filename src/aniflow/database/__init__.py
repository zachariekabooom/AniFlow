"""Persistance locale SQLite : connexion, migrations, sauvegarde/restauration, paramètres, cache."""

from .backup import BackupInfo, backup_database, list_backups, restore_database, verify_database_file
from .bootstrap import open_app_database
from .connection import connect
from .errors import (
    DatabaseCorruptError,
    DatabaseError,
    DatabaseRestoreError,
    DatabaseTooNewError,
    MigrationError,
    SettingsError,
)
from .http_cache import SqliteResponseCache
from .migrations import LATEST_VERSION, MIGRATIONS, Migration, current_version, migrate
from .settings import SETTINGS, SettingsStore

__all__ = [
    "BackupInfo", "DatabaseCorruptError", "DatabaseError", "DatabaseRestoreError", "DatabaseTooNewError",
    "LATEST_VERSION", "MIGRATIONS", "Migration", "MigrationError", "SETTINGS", "SettingsError", "SettingsStore",
    "SqliteResponseCache", "backup_database", "connect", "current_version", "list_backups", "migrate",
    "open_app_database", "restore_database", "verify_database_file",
]
