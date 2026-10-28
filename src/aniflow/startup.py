"""Contrôles de démarrage, sans Qt : dossier de données, journal, base SQLite migrée, paramètres.

`run_startup_checks` ne lève jamais : il retourne soit un `StartupContext` (l'appelant doit fermer la
connexion), soit un `StartupFailure` dont le message français est affichable tel quel (boîte de dialogue à
l'étape E2). Le détail technique va au journal, jamais à l'écran.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from aniflow.database import (
    DatabaseError,
    DatabaseTooNewError,
    MigrationError,
    SettingsStore,
    open_app_database,
)
from aniflow.logging_setup import setup_logging
from aniflow.paths import AppPaths

log = logging.getLogger(__name__)

EXIT_UNEXPECTED = 1
EXIT_DATABASE = 2
EXIT_DATA_FOLDER = 3


@dataclass(frozen=True)
class StartupFailure:
    title: str
    user_message: str  # français, affichable tel quel
    exit_code: int
    technical: str  # pour le journal uniquement
    log_path: Path | None = None


@dataclass(frozen=True)
class StartupContext:
    paths: AppPaths
    connection: sqlite3.Connection  # à fermer par l'appelant
    settings: SettingsStore
    log_path: Path | None


def _technical(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"


def _folder_failure(paths: AppPaths, exc: BaseException, log_path: Path | None) -> StartupFailure:
    return StartupFailure(
        "Dossier de données inaccessible",
        f"AniFlow ne peut pas utiliser son dossier de données :\n{paths.root}\n\n"
        "Vérifiez que le disque est accessible, qu'il reste de la place et que vous avez le droit d'écrire "
        "dans ce dossier, puis relancez AniFlow.",
        EXIT_DATA_FOLDER,
        _technical(exc),
        log_path,
    )


def _unreadable_failure(paths: AppPaths, exc: BaseException, log_path: Path | None) -> StartupFailure:
    return StartupFailure(
        "Base de données illisible",
        f"Le fichier de base de données est illisible ou corrompu :\n{paths.database}\n\n"
        "AniFlow n'a pas tenté de le réparer. Vos sauvegardes se trouvent dans :\n"
        f"{paths.backups}\n\n"
        "La restauration guidée sera ajoutée plus tard. En attendant, fermez AniFlow et remplacez le "
        "fichier de base par une copie d'une sauvegarde.",
        EXIT_DATABASE,
        _technical(exc),
        log_path,
    )


def run_startup_checks(paths: AppPaths | None = None, *, configure_logging: bool = True) -> StartupContext | StartupFailure:
    paths = paths or AppPaths.default()
    log_path: Path | None = None
    try:
        paths.ensure()
    except OSError as exc:
        log.error("Dossier de données inutilisable : %s", _technical(exc))
        return _folder_failure(paths, exc, None)
    if configure_logging:
        try:
            log_path = setup_logging(paths.logs)
        except OSError as exc:  # un journal indisponible ne doit pas empêcher de démarrer
            log.error("Journal fichier indisponible : %s", _technical(exc))

    try:
        connection = open_app_database(paths)
    except DatabaseTooNewError as exc:
        failure = StartupFailure("Base de données plus récente", exc.user_message, EXIT_DATABASE, _technical(exc), log_path)
    except MigrationError as exc:
        failure = StartupFailure("Mise à jour de la base impossible", exc.user_message, EXIT_DATABASE, _technical(exc), log_path)
    except DatabaseError as exc:
        failure = _unreadable_failure(paths, exc, log_path)
    except sqlite3.OperationalError as exc:
        if "unable to open" in str(exc).lower():
            failure = _folder_failure(paths, exc, log_path)
        else:
            log.exception("Erreur SQLite inattendue au démarrage")
            failure = _unexpected(exc, log_path)
    except sqlite3.DatabaseError as exc:  # « file is not a database », etc.
        failure = _unreadable_failure(paths, exc, log_path)
    except OSError as exc:
        failure = _folder_failure(paths, exc, log_path)
    except Exception as exc:  # dernier filet : le démarrage ne doit jamais s'achever sur une trace
        log.exception("Erreur inattendue au démarrage")
        failure = _unexpected(exc, log_path)
    else:
        return StartupContext(paths, connection, SettingsStore(connection), log_path)

    log.error("Démarrage impossible (code %d) : %s", failure.exit_code, failure.technical)
    return failure


def _unexpected(exc: BaseException, log_path: Path | None) -> StartupFailure:
    where = f"\nLe détail est enregistré dans le journal :\n{log_path}" if log_path else ""
    return StartupFailure(
        "Démarrage impossible",
        f"AniFlow n'a pas pu démarrer à cause d'une erreur inattendue.{where}",
        EXIT_UNEXPECTED,
        _technical(exc),
        log_path,
    )
