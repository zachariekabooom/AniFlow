"""Point d'entrée : `python -m aniflow` (ou la commande `aniflow`).

Ordre : arguments → contrôles de démarrage (sans Qt) → vérification de PySide6 → fenêtre. Une erreur de démarrage
n'affiche jamais de trace : message français (boîte de dialogue, ou stderr en --smoke-test), détail au journal et code
de sortie dédié (voir aniflow.startup : 1 inattendu, 2 base de données, 3 dossier de données, 4 PySide6, 5 smoke-test).
"""

from __future__ import annotations

import argparse
import logging
import sqlite3
import sys
from typing import Sequence

from aniflow.paths import AppPaths
from aniflow.startup import EXIT_QT_MISSING, EXIT_UNEXPECTED, StartupContext, StartupFailure, run_startup_checks

log = logging.getLogger(__name__)

QT_MISSING_MESSAGE = (
    "AniFlow a besoin de PySide6 pour afficher sa fenêtre, mais il est introuvable ou inutilisable.\n"
    "Installez-le avec : pip install PySide6   (ou, depuis le dépôt : pip install -e .[ui])"
)
UNEXPECTED_MESSAGE = "AniFlow a rencontré une erreur inattendue et n'a pas pu démarrer."


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="aniflow", add_help=False, description="AniFlow — bibliothèque personnelle d'animés.")
    parser.add_argument("-h", "--help", action="help", help="affiche cette aide puis quitte")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="démarre l'application, vérifie qu'elle s'initialise correctement puis quitte (code 0 si tout va bien) ; n'enregistre aucune préférence",
    )
    return parser.parse_args(argv)


def _force_utf8_streams() -> None:
    """Sortie UTF-8 quelle que soit la page de code de la console (cp1252 par défaut sous Windows pour un tube)."""
    for stream, errors in ((sys.stdout, "strict"), (sys.stderr, "backslashreplace")):
        reconfigure = getattr(stream, "reconfigure", None)  # absent si la sortie est None (pythonw) ou remplacée
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors=errors)


def _say(message: str) -> None:
    if sys.stderr is not None:
        print(message, file=sys.stderr)


def _close_quietly(connection: sqlite3.Connection) -> None:
    try:
        connection.close()
    except sqlite3.Error:
        log.warning("Fermeture de la base impossible", exc_info=True)


def _qt_available() -> bool:
    try:
        import PySide6.QtWidgets  # noqa: F401 — la dépendance réelle de l'interface
    except ImportError as exc:
        log.error("PySide6 indisponible : %s", exc)
        return False
    return True


def _report_failure(failure: StartupFailure, args: argparse.Namespace) -> int:
    _say(f"{failure.title}\n\n{failure.user_message}")
    if not args.smoke_test and _qt_available():
        try:
            from aniflow.ui import application

            application.show_failure_dialog(failure)
        except Exception:  # noqa: BLE001 — le message est déjà sur stderr ; la boîte de dialogue est un confort
            log.exception("Boîte de dialogue d'erreur de démarrage impossible")
    return failure.exit_code


def _launch(args: argparse.Namespace, context: StartupContext) -> int:
    if not _qt_available():
        _say(QT_MISSING_MESSAGE)
        return EXIT_QT_MISSING
    from aniflow.ui import application

    return application.run(args, context)


def main(argv: Sequence[str] | None = None) -> int:
    _force_utf8_streams()  # d'abord : l'aide et les erreurs d'arguments contiennent aussi des accents
    args = parse_args(argv)
    try:
        outcome = run_startup_checks()
        if isinstance(outcome, StartupFailure):
            return _report_failure(outcome, args)
        try:
            return _launch(args, outcome)
        finally:
            _close_quietly(outcome.connection)  # jamais de connexion laissée ouverte, quoi qu'il arrive
    except Exception:  # noqa: BLE001 — dernier filet : le lancement ne doit jamais s'achever sur une trace
        log.exception("Erreur non gérée pendant le lancement")
        _say(f"{UNEXPECTED_MESSAGE}\nLe détail est enregistré dans le journal : {AppPaths.default().logs / 'aniflow.log'}")
        return EXIT_UNEXPECTED
