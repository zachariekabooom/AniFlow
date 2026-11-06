"""Application Qt : thème, paramètres régionaux, pont des messages Qt, fenêtre principale, boucle d'événements.

Ce module importe PySide6 : `aniflow.app` ne le charge qu'après avoir vérifié que PySide6 est disponible.
"""

from __future__ import annotations

import locale
import logging
import sys
from typing import Any, Callable, Sequence

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox

from aniflow import APP_NAME, __version__
from aniflow.paths import logo_path
from aniflow.startup import EXIT_SMOKE_TEST_FAILED, StartupContext, StartupFailure
from aniflow.ui.main_window import MainWindow
from aniflow.ui.qt_logging import QtMessageRecorder, current_recorder, install_qt_message_handler, uninstall_qt_message_handler
from aniflow.ui.smoke import SmokeFacts, smoke_problems
from aniflow.ui.theme import build_stylesheet
from aniflow.ui.theme.qt_palette import build_palette

log = logging.getLogger(__name__)

SMOKE_WATCHDOG_MS = 15_000  # garde-fou : le smoke-test ne doit jamais rester bloqué


BASE_STYLE = "Fusion"
BASE_STYLE_PROPERTY = "aniflowBaseStyle"  # propriété dynamique de QApplication : nom du style de base posé par apply_theme


def base_style_name(app: QApplication) -> str:
    """Nom du style de base posé par apply_theme (« fusion »), ou « » s'il n'a pas pu l'être.

    Avec une feuille de style d'application, QApplication.style() renvoie le proxy QStyleSheetStyle de Qt : son nom
    d'objet est vide et sa classe n'est pas celle du style de base. On lit donc la trace laissée par apply_theme.
    """
    value = app.property(BASE_STYLE_PROPERTY)
    return value if isinstance(value, str) else ""


def apply_theme(app: QApplication) -> None:
    """Style Fusion (rendu prévisible de la feuille de style) + palette sombre issue des jetons + feuille de style.

    Qt ≥ 6.4 : une palette d'application sombre donne une barre de titre sombre sous Windows (à confirmer visuellement).
    Le style de base est relevé sur l'objet que renvoie setStyle() — le style créé, jamais le proxy de la feuille de
    style —, journalisé et mémorisé (voir base_style_name) ; le smoke-test refuse de démarrer sans Fusion.
    """
    style = app.setStyle(BASE_STYLE)
    base_name = style.objectName().lower() if style is not None else ""
    base_class = style.metaObject().className() if style is not None else ""
    app.setProperty(BASE_STYLE_PROPERTY, base_name)
    if base_name == BASE_STYLE.lower():
        log.info("Style de base : %s (classe Qt %s)", base_name, base_class)
    else:
        log.warning("Le style %s n'a pas pu être appliqué : style obtenu %r (classe %r)", BASE_STYLE, base_name, base_class)
    try:
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)  # Qt ≥ 6.8 ; avant la palette, qui doit rester la nôtre
    except AttributeError:
        log.debug("QStyleHints.setColorScheme indisponible : palette sombre seule")
    app.setPalette(build_palette())
    app.setStyleSheet(build_stylesheet())


def create_application(argv: Sequence[str] | None = None) -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication(list(argv) if argv else [APP_NAME.lower()])
    # Qt relit les paramètres régionaux du système à la création de l'application : libmpv exige LC_NUMERIC = « C ».
    locale.setlocale(locale.LC_NUMERIC, "C")
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    apply_theme(app)
    return app


def show_failure_dialog(failure: StartupFailure) -> None:
    """Boîte de dialogue d'erreur de démarrage : message français uniquement, jamais le détail technique."""
    create_application()
    box = QMessageBox(QMessageBox.Icon.Critical, failure.title, failure.user_message, QMessageBox.StandardButton.Close)
    box.setTextFormat(Qt.TextFormat.PlainText)
    box.exec()


def _window_icon() -> QIcon | None:
    path = logo_path()
    if path is None:
        return None
    pixmap = QPixmap(str(path))
    return None if pixmap.isNull() else QIcon(pixmap)


def collect_smoke_facts(app: QApplication, window: MainWindow, recorder: QtMessageRecorder) -> SmokeFacts:
    navigation = window.navigation
    return SmokeFacts(
        window_visible=window.isVisible(),
        sections_shown=window.stack.count(),
        sections_expected=len(navigation.sections),
        navigation_in_sync=window.stack.currentIndex() == navigation.index and window.sidebar.buttons[navigation.current.id].isChecked(),
        theme_applied=bool(app.styleSheet().strip()),
        lc_numeric=locale.setlocale(locale.LC_NUMERIC),
        base_style=base_style_name(app),
        style_warnings=tuple(recorder.style_warnings()),
    )


def _say(message: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    if stream is not None:  # sans console (pythonw, double-clic), les flux standard valent None
        print(message, file=stream)


def _finish_smoke(app: QApplication, window: MainWindow, recorder: QtMessageRecorder) -> None:
    problems = smoke_problems(collect_smoke_facts(app, window, recorder))
    if problems:
        log.error("Smoke-test en échec : %s", "; ".join(problems))
        _say("AniFlow : démarrage incomplet :\n- " + "\n- ".join(problems), error=True)
        app.exit(EXIT_SMOKE_TEST_FAILED)
        return
    log.info("Smoke-test : démarrage OK")
    _say("AniFlow : démarrage OK (smoke-test)")
    app.exit(0)


def _smoke_watchdog(app: QApplication) -> None:
    log.error("Smoke-test : délai de %d ms dépassé", SMOKE_WATCHDOG_MS)
    _say("AniFlow : démarrage trop long, smoke-test interrompu.", error=True)
    app.exit(EXIT_SMOKE_TEST_FAILED)


def run(
    args: Any,
    context: StartupContext,
    *,
    recorder: QtMessageRecorder | None = None,
    on_started: Callable[[MainWindow, QApplication], None] | None = None,
) -> int:
    """Affiche la fenêtre principale et exécute la boucle d'événements ; retourne le code de sortie.

    La connexion SQLite de `context` reste à la charge de l'appelant (aniflow.app.main la ferme toujours).
    `on_started(window, app)` est appelé juste après l'affichage (utilisé par les tests).
    """
    smoke = bool(getattr(args, "smoke_test", False))
    owns_handler = False
    if recorder is None:
        recorder = current_recorder()
        if recorder is None:
            recorder = install_qt_message_handler(echo_stderr=True)
            owns_handler = True  # installé ici : retiré ici (un rappel Python resté enregistré pendant l'arrêt de l'interpréteur est dangereux)
    app = create_application()
    icon = _window_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    timers: list[QTimer] = []

    def after(delay_ms: int, callback: Callable[[], None]) -> None:
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(callback)
        timer.start(delay_ms)
        timers.append(timer)  # référence conservée ; tous sont arrêtés en sortie (un minuteur oublié se déclencherait dans la boucle suivante)

    window = MainWindow(context.settings, logo=logo_path(), persist=not smoke)
    try:
        window.show()
        if smoke:
            after(0, lambda: _finish_smoke(app, window, recorder))
            after(SMOKE_WATCHDOG_MS, lambda: _smoke_watchdog(app))
        if on_started is not None:
            on_started(window, app)
        code = app.exec()
    finally:
        for timer in timers:
            timer.stop()
        window.close()  # smoke-test : la fenêtre est encore ouverte ; la fermeture n'enregistre rien (persist=False)
        app.processEvents()
        if owns_handler:
            uninstall_qt_message_handler()
    return code
