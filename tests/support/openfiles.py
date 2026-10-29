"""Détection d'un fichier encore ouvert par le processus de test.

Sous Windows, un fichier ouvert ne peut être ni supprimé ni renommé (WinError 32) : c'est ce qui fait échouer le
nettoyage d'un dossier temporaire quand une connexion SQLite fuit. Sous Linux, la suppression réussit toujours ;
la fuite est alors détectée par la lecture de /proc/self/fd.
"""

from __future__ import annotations

import gc
import os
import unittest
from pathlib import Path


def without_garbage_collector(test_case: unittest.TestCase) -> None:
    """Désactive le ramasse-miettes cyclique pendant le test.

    Depuis Python 3.11, une sqlite3.Connection abandonnée n'est libérée que par ce ramasse-miettes (cycle avec son
    cache d'instructions) : sans fermeture explicite, le fichier reste ouvert un temps indéterminé. Un test qui
    le laisse actif peut donc réussir par hasard ; avec lui coupé, la fermeture doit être explicite.
    """
    gc.collect()
    gc.disable()
    test_case.addCleanup(gc.enable)


def open_paths() -> set[str] | None:
    """Chemins des fichiers ouverts par ce processus (Linux), ou None si le système ne le permet pas."""
    fd_dir = Path("/proc/self/fd")
    if not fd_dir.is_dir():
        return None
    found: set[str] = set()
    for entry in fd_dir.iterdir():
        try:
            found.add(os.readlink(entry))
        except OSError:
            continue  # descripteur fermé entre-temps
    return found


def assert_released_then_delete(test_case: unittest.TestCase, path: str | Path) -> None:
    """Échoue si `path` (ou son -wal / -shm) est encore ouvert, puis supprime le fichier.

    Linux : lecture de /proc/self/fd. Windows : la suppression lève PermissionError (WinError 32) si une
    connexion fuit.
    """
    resolved = str(Path(path).resolve())
    opened = open_paths()
    if opened is not None:
        still_open = sorted(p for p in opened if p.startswith(resolved))
        test_case.assertEqual(still_open, [], f"fichier encore ouvert par le processus : {still_open}")
    os.remove(path)
