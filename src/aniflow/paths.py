"""Chemins de l'application : ressources du dépôt et dossiers de données utilisateur."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

LOGO_RELATIVE_PATH = Path("docs") / "branding" / "aniflow-logo-final.png"


def project_root() -> Path:
    """Racine du dépôt (exécution depuis les sources) ou du paquet figé (PyInstaller).

    Les ressources du dépôt (logo, etc.) sont lues depuis cette racine. L'empaquetage
    Windows (phase 7) devra les embarquer explicitement.
    """
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root)
    return Path(__file__).resolve().parents[2]


def logo_path(root: Path | None = None) -> Path | None:
    """Chemin du logo approuvé, ou None s'il est absent (jamais de logo de remplacement)."""
    candidate = (root or project_root()) / LOGO_RELATIVE_PATH
    return candidate if candidate.is_file() else None


def app_data_dir() -> Path:
    """Dossier des données utilisateur (base, sauvegardes, journaux).

    Surchargeable avec la variable d'environnement ANIFLOW_HOME (tests, mode portable).
    """
    override = os.environ.get("ANIFLOW_HOME")
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "AniFlow"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "aniflow"


@dataclass(frozen=True)
class AppPaths:
    """Emplacements des données utilisateur, dérivés d'un unique dossier racine."""

    root: Path

    @classmethod
    def default(cls) -> "AppPaths":
        return cls(app_data_dir())

    @property
    def database(self) -> Path:
        return self.root / "aniflow.db"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    def ensure(self) -> "AppPaths":
        for folder in (self.root, self.backups, self.logs):
            folder.mkdir(parents=True, exist_ok=True)
        return self
