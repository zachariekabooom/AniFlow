"""Pont des messages Qt vers le journal Python (aucun import de PySide6 à l'import du module).

Qt n'écrit ses avertissements que sur stderr, perdus quand l'application est lancée sans console. Ici ils vont au
journal (logger « aniflow.qt »). Les avertissements de FEUILLE DE STYLE (erreur de syntaxe QSS, propriété inconnue)
sont repérés à part : ils signalent un thème mal appliqué.
"""

from __future__ import annotations

import logging
import sys
import threading
from collections import Counter
from typing import Any

STYLE_MARKERS = ("Could not parse", "Unknown property", "Unknown pseudo")
MAX_LOGGED_REPEATS = 3
_MAX_KEPT_MESSAGES = 500
_LEVELS = {
    "QtDebugMsg": logging.DEBUG,
    "QtInfoMsg": logging.INFO,
    "QtWarningMsg": logging.WARNING,
    "QtCriticalMsg": logging.ERROR,
    "QtFatalMsg": logging.CRITICAL,
}


def level_of(mode: Any) -> int:
    """Niveau logging d'un QtMsgType (ou de son nom) ; inconnu = WARNING."""
    name = str(getattr(mode, "name", None) or mode)
    return _LEVELS.get(name.rsplit(".", 1)[-1], logging.WARNING)


class QtMessageRecorder:
    """Gestionnaire de messages Qt : journalise (sans répétition infinie) et mémorise pour les contrôles."""

    def __init__(self, *, echo_stderr: bool = False, logger: logging.Logger | None = None) -> None:
        self._echo = echo_stderr
        self._log = logger or logging.getLogger("aniflow.qt")
        self._lock = threading.Lock()
        self._counts: Counter[tuple[int, str]] = Counter()
        self.messages: list[tuple[int, str]] = []

    def handle(self, mode: Any, context: Any, message: str) -> None:
        """Signature imposée par qInstallMessageHandler : ne doit jamais lever d'exception."""
        try:
            level = level_of(mode)
            with self._lock:
                self._counts[(level, message)] += 1
                count = self._counts[(level, message)]
                if len(self.messages) < _MAX_KEPT_MESSAGES:
                    self.messages.append((level, message))
            if count <= MAX_LOGGED_REPEATS:
                self._log.log(level, "%s", message)
            elif count == MAX_LOGGED_REPEATS + 1:
                self._log.log(level, "(message Qt répété : la suite est masquée) %s", message)
            if self._echo and level >= logging.WARNING and sys.stderr is not None:
                print(f"Qt : {message}", file=sys.stderr)
        except Exception:  # noqa: BLE001 — un gestionnaire de messages Qt ne doit jamais propager
            pass

    def style_warnings(self) -> list[str]:
        with self._lock:
            kept = list(self.messages)
        return [m for level, m in kept if level >= logging.WARNING and any(marker in m for marker in STYLE_MARKERS)]


_installed: QtMessageRecorder | None = None
_previous_handler: Any = None
_active_callable: Any = None  # référence conservée : Qt n'en garde pas de copie Python


def install_qt_message_handler(recorder: QtMessageRecorder | None = None, *, echo_stderr: bool = False) -> QtMessageRecorder:
    from PySide6.QtCore import qInstallMessageHandler  # import tardif : le module reste importable sans PySide6

    global _installed, _previous_handler, _active_callable
    if _installed is not None:
        uninstall_qt_message_handler()
    recorder = recorder or QtMessageRecorder(echo_stderr=echo_stderr)
    _active_callable = recorder.handle
    _previous_handler = qInstallMessageHandler(_active_callable)
    _installed = recorder
    return recorder


def uninstall_qt_message_handler() -> None:
    from PySide6.QtCore import qInstallMessageHandler

    global _installed, _previous_handler, _active_callable
    qInstallMessageHandler(_previous_handler)  # None = gestionnaire par défaut de Qt
    _installed, _previous_handler, _active_callable = None, None, None


def current_recorder() -> QtMessageRecorder | None:
    return _installed
