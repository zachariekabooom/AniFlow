"""Sauvegarde et restauration de la base SQLite.

AniFlow ne supprime jamais de sauvegarde automatiquement (SPEC §5/§13) : toute rotation sera une
action explicite de l'utilisateur.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .errors import DatabaseCorruptError, DatabaseRestoreError, DatabaseTooNewError

_NAME = re.compile(r"^aniflow-(\d{8}-\d{6}-\d{6})-(.+)\.db$")


@dataclass(frozen=True)
class BackupInfo:
    path: Path
    tag: str
    size_bytes: int


def verify_database_file(path: Path) -> int:
    """Contrôle d'intégrité complet. Retourne PRAGMA user_version ou lève DatabaseCorruptError."""
    path = Path(path)
    if not path.is_file():
        raise DatabaseCorruptError(f"fichier introuvable : {path}")
    conn = None
    try:
        conn = sqlite3.connect(str(path))
        result = conn.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise DatabaseCorruptError(f"contrôle d'intégrité négatif : {result}")
        return int(conn.execute("PRAGMA user_version").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        raise DatabaseCorruptError(str(exc)) from exc
    finally:
        if conn is not None:
            conn.close()


def backup_database(conn: sqlite3.Connection, backups_dir: Path, *, tag: str = "manual", now: datetime | None = None) -> Path:
    """Copie cohérente de la base ouverte (API de sauvegarde SQLite, compatible WAL), vérifiée avant publication."""
    backups_dir = Path(backups_dir)
    backups_dir.mkdir(parents=True, exist_ok=True)
    safe_tag = re.sub(r"[^A-Za-z0-9._-]+", "-", tag).strip("-") or "manual"
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S-%f")
    destination = backups_dir / f"aniflow-{stamp}-{safe_tag}.db"
    partial = destination.with_name(destination.name + ".part")
    target = sqlite3.connect(str(partial))
    try:
        conn.backup(target)
        target.execute("PRAGMA journal_mode = DELETE")  # sauvegarde en un seul fichier
    except BaseException:
        target.close()
        partial.unlink(missing_ok=True)
        raise
    target.close()
    try:
        verify_database_file(partial)
        os.replace(partial, destination)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    return destination


def list_backups(backups_dir: Path) -> list[BackupInfo]:
    backups_dir = Path(backups_dir)
    if not backups_dir.is_dir():
        return []
    found = []
    for item in sorted(backups_dir.iterdir()):
        match = _NAME.match(item.name)
        if match and item.is_file():
            found.append(BackupInfo(item, match.group(2), item.stat().st_size))
    return found


def restore_database(backup_path: Path, db_path: Path, backups_dir: Path) -> Path | None:
    """Remplace la base par une sauvegarde vérifiée. Aucune connexion ne doit être ouverte sur db_path.

    Retourne le chemin de la sauvegarde de sécurité de l'ancienne base (None si elle n'existait pas).
    En cas d'échec, la base actuelle reste intacte.
    """
    from .migrations import LATEST_VERSION  # import tardif : évite une dépendance circulaire

    backup_path, db_path = Path(backup_path), Path(db_path)
    if not backup_path.is_file():
        raise DatabaseRestoreError(
            f"sauvegarde introuvable : {backup_path}",
            user_message="Le fichier de sauvegarde choisi est introuvable ; la base actuelle n'a pas été modifiée.",
        )
    db_path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".aniflow-restore-", dir=db_path.parent))
    try:
        staged = staging / "staged.db"
        shutil.copy2(backup_path, staged)
        version = verify_database_file(staged)
        if version > LATEST_VERSION:
            raise DatabaseTooNewError(version, LATEST_VERSION)

        safety: Path | None = None
        if db_path.exists():
            try:
                live = sqlite3.connect(str(db_path))
                try:
                    safety = backup_database(live, backups_dir, tag="pre-restore")
                finally:
                    live.close()
            except (sqlite3.Error, DatabaseCorruptError):
                backups_dir.mkdir(parents=True, exist_ok=True)
                safety = backups_dir / f"aniflow-{datetime.now():%Y%m%d-%H%M%S-%f}-pre-restore-raw.db"
                shutil.copy2(db_path, safety)

        try:
            os.replace(staged, db_path)
        except OSError as exc:  # Windows : fichier ouvert par une autre connexion
            raise DatabaseRestoreError(f"remplacement impossible : {exc}") from exc
        for suffix in ("-wal", "-shm"):  # un journal périmé corromprait la base restaurée
            Path(str(db_path) + suffix).unlink(missing_ok=True)
        return safety
    finally:
        shutil.rmtree(staging, ignore_errors=True)
