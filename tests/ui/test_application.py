"""Création de l'application Qt, thème, mode --smoke-test et boucle d'événements (PySide6, hors écran par défaut)."""

import locale
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock

from aniflow.paths import AppPaths
from aniflow.startup import EXIT_SMOKE_TEST_FAILED, StartupContext, StartupFailure, run_startup_checks
from aniflow.ui.theme import DEFAULT_PALETTE, build_stylesheet
from tests.support.openfiles import assert_released_then_delete, without_garbage_collector
from tests.support.qt import HAS_QT, requires_qt

if HAS_QT:
    from PySide6.QtCore import QThreadPool, QTimer
    from PySide6.QtGui import QPalette
    from aniflow.ui import application
    from aniflow.ui.application import base_style_name, collect_smoke_facts, create_application, run, show_failure_dialog
    from aniflow.ui.main_window import MainWindow
    from aniflow.ui.qt_logging import QtMessageRecorder, current_recorder, install_qt_message_handler, uninstall_qt_message_handler


@requires_qt
class ApplicationCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.paths = AppPaths(Path(tmp.name) / "AniFlowData")
        self.started = run_startup_checks(self.paths, configure_logging=False)
        self.assertIsInstance(self.started, StartupContext, getattr(self.started, "user_message", self.started))
        self.addCleanup(self.started.connection.close)
        self.app.closeAllWindows()  # aucune fenêtre d'un test précédent : la boucle doit pouvoir s'arrêter

    def guard_against_a_stuck_loop(self, milliseconds=20_000):
        guard = QTimer()
        guard.setSingleShot(True)
        guard.timeout.connect(self.app.quit)
        guard.start(milliseconds)
        self.addCleanup(guard.stop)


@requires_qt
class ThemeTests(ApplicationCase):
    def test_application_is_created_with_the_dark_theme_and_the_numeric_locale_libmpv_needs(self):
        app = create_application()
        self.assertIs(app, self.app)
        self.assertEqual(app.applicationName(), "AniFlow")
        self.assertIn(DEFAULT_PALETTE.bg, app.styleSheet())
        self.assertEqual(locale.setlocale(locale.LC_NUMERIC), "C")

    def test_fusion_is_the_base_style_even_though_the_stylesheet_hides_it(self):
        """Avec une feuille de style d'application, QApplication.style() renvoie le proxy QStyleSheetStyle de Qt : nom d'objet
        vide, classe du proxy. Le style de base se vérifie donc (1) sur la trace notée par apply_theme au moment où il est
        posé, puis (2) sur le style réel, rendu par Qt une fois la feuille retirée.
        """
        app = create_application()
        self.addCleanup(create_application)  # le thème est toujours remis, même si une assertion échoue
        self.assertEqual(base_style_name(app), "fusion")
        app.setStyleSheet("")  # Qt rend alors le style de base à la place du proxy
        real = app.style()
        self.assertEqual((real.objectName().lower(), real.metaObject().className()), ("fusion", "QFusionStyle"), "le style réellement utilisé n'est pas Fusion")
        create_application()  # le thème complet (style, palette, feuille) est réappliqué : il doit l'être intégralement
        self.assertIn(DEFAULT_PALETTE.bg, app.styleSheet())
        self.assertIn(DEFAULT_PALETTE.accent, app.styleSheet())
        self.assertEqual(app.palette().color(QPalette.ColorRole.Window).name().lower(), DEFAULT_PALETTE.bg.lower())
        self.assertEqual(base_style_name(app), "fusion")

    def test_the_smoke_test_reads_the_same_base_style(self):
        window = MainWindow(None)
        self.addCleanup(window.close)
        window.show()
        self.app.processEvents()
        facts = collect_smoke_facts(self.app, window, QtMessageRecorder())
        self.assertEqual(facts.base_style, "fusion")
        self.assertTrue(facts.theme_applied)

    def test_the_palette_comes_from_the_tokens_and_is_dark(self):
        palette = self.app.palette()
        self.assertEqual(palette.color(QPalette.ColorRole.Window).name().lower(), DEFAULT_PALETTE.bg.lower())
        self.assertEqual(palette.color(QPalette.ColorRole.WindowText).name().lower(), DEFAULT_PALETTE.text.lower())
        self.assertGreater(palette.color(QPalette.ColorRole.WindowText).lightness(), palette.color(QPalette.ColorRole.Window).lightness())

    def test_calling_create_application_again_is_harmless(self):
        for _ in range(3):
            self.assertIs(create_application(), self.app)
        self.assertEqual(locale.setlocale(locale.LC_NUMERIC), "C")

    def test_qt_accepts_the_stylesheet_without_any_style_warning(self):
        recorder = install_qt_message_handler(QtMessageRecorder())
        self.addCleanup(uninstall_qt_message_handler)
        self.app.setStyleSheet("")
        self.app.setStyleSheet(build_stylesheet())
        window = MainWindow(None)
        self.addCleanup(window.close)
        window.show()
        self.app.processEvents()
        self.assertEqual(recorder.style_warnings(), [], "Qt signale un problème dans la feuille de style")


@requires_qt
class SmokeTestRunTests(ApplicationCase):
    def test_smoke_test_returns_zero_and_stores_nothing(self):
        self.guard_against_a_stuck_loop()
        code = run(Namespace(smoke_test=True), self.started, recorder=QtMessageRecorder())
        self.assertEqual(code, 0)
        self.assertIsNone(self.started.settings.get("ui.window_geometry"))
        self.assertEqual(self.started.settings.get("ui.last_section"), "accueil")

    def test_smoke_test_reports_a_failed_check_with_the_dedicated_exit_code(self):
        self.guard_against_a_stuck_loop()
        recorder = QtMessageRecorder()
        recorder.handle(type("Mode", (), {"name": "QtWarningMsg"})(), None, "Could not parse application stylesheet")
        code = run(Namespace(smoke_test=True), self.started, recorder=recorder)
        self.assertEqual(code, EXIT_SMOKE_TEST_FAILED)

    def test_the_database_file_is_released_after_a_complete_run(self):
        without_garbage_collector(self)  # aucune connexion ne doit dépendre du ramasse-miettes
        self.guard_against_a_stuck_loop()
        self.assertEqual(run(Namespace(smoke_test=True), self.started, recorder=QtMessageRecorder()), 0)
        self.started.connection.close()
        assert_released_then_delete(self, self.paths.database)

    def test_no_background_thread_is_left_running(self):
        self.guard_against_a_stuck_loop()
        run(Namespace(smoke_test=True), self.started, recorder=QtMessageRecorder())
        self.assertEqual(QThreadPool.globalInstance().activeThreadCount(), 0)


@requires_qt
class NormalRunTests(ApplicationCase):
    def test_a_normal_start_saves_the_state_when_the_window_closes(self):
        self.guard_against_a_stuck_loop()

        def started(window, app):
            window.navigation.go_to("telechargements")
            QTimer.singleShot(50, window.close)

        code = run(Namespace(smoke_test=False), self.started, recorder=QtMessageRecorder(), on_started=started)
        self.assertEqual(code, 0)
        self.assertEqual(self.started.settings.get("ui.last_section"), "telechargements")
        self.assertTrue(self.started.settings.get("ui.window_geometry"))

    def test_a_message_handler_installed_by_the_run_is_removed_when_it_ends(self):
        uninstall_qt_message_handler()
        self.assertIsNone(current_recorder())
        self.guard_against_a_stuck_loop()
        self.assertEqual(run(Namespace(smoke_test=True), self.started), 0)  # sans enregistreur injecté : le sien, réellement branché sur Qt
        self.assertIsNone(current_recorder())

    def test_a_handler_installed_by_the_caller_is_left_alone(self):
        recorder = install_qt_message_handler(QtMessageRecorder())
        self.addCleanup(uninstall_qt_message_handler)
        self.guard_against_a_stuck_loop()
        self.assertEqual(run(Namespace(smoke_test=True), self.started), 0)
        self.assertIs(current_recorder(), recorder)

    def test_no_timer_outlives_the_run(self):
        """Un minuteur oublié se déclencherait dans la boucle d'un test suivant : le garde-fou du smoke-test doit être arrêté."""
        self.guard_against_a_stuck_loop()
        self.assertEqual(run(Namespace(smoke_test=True), self.started, recorder=QtMessageRecorder()), 0)
        self.guard_against_a_stuck_loop()

        def started(window, app):
            QTimer.singleShot(50, window.close)

        self.assertEqual(run(Namespace(smoke_test=False), self.started, recorder=QtMessageRecorder(), on_started=started), 0)


@requires_qt
class FailureDialogTests(ApplicationCase):
    def test_the_dialog_shows_the_title_and_the_user_message_but_never_the_technical_detail(self):
        failure = StartupFailure("Base de données plus récente", "Message pour l'utilisateur.", 2, "DatabaseTooNewError: DETAIL-TECHNIQUE", None)
        with mock.patch.object(application, "QMessageBox") as box_class:
            show_failure_dialog(failure)
        arguments = " ".join(str(a) for a in box_class.call_args.args)
        self.assertIn("Message pour l'utilisateur.", arguments)
        self.assertIn("Base de données plus récente", arguments)
        self.assertNotIn("DETAIL-TECHNIQUE", arguments)
        box_class.return_value.exec.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
