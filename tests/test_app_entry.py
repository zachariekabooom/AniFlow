"""Point d'entrée `python -m aniflow` : arguments, erreurs de démarrage, codes de sortie, connexion toujours fermée.

Ces tests n'exigent pas PySide6 : les échecs de démarrage sont traités avant tout import de Qt.
"""

import contextlib
import hashlib
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aniflow import app as app_module
from aniflow.paths import AppPaths
from aniflow.startup import (
    EXIT_DATA_FOLDER,
    EXIT_DATABASE,
    EXIT_QT_MISSING,
    EXIT_UNEXPECTED,
    StartupContext,
    StartupFailure,
)
from tests.support.subproc import run_python


class TempDirCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.home = self.dir / "AniFlowData"

    def sha(self, path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ParseArgsTests(unittest.TestCase):
    def test_defaults_and_smoke_test_flag(self):
        self.assertFalse(app_module.parse_args([]).smoke_test)
        self.assertTrue(app_module.parse_args(["--smoke-test"]).smoke_test)

    def test_unknown_argument_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            app_module.parse_args(["--inconnu"])
        self.assertEqual(ctx.exception.code, 2)


class EntryPointProcessTests(TempDirCase):
    """`python -m aniflow` lancé comme sur un PC Windows en français (tube cp1252, décodage strict des sorties)."""

    def test_help_describes_the_smoke_test_option(self):
        result = run_python("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--smoke-test", result.stdout)
        self.assertIn("affiche cette aide", result.stdout)

    def test_without_pyside6_the_message_is_clear_and_the_exit_code_is_4(self):
        code = "import sys; sys.modules['PySide6'] = None; from aniflow.app import main; sys.exit(main(['--smoke-test']))"
        result = run_python(home=self.home, code=code)
        self.assertEqual(result.returncode, EXIT_QT_MISSING, result.stderr)
        self.assertIn("PySide6", result.stderr)
        self.assertIn("pip install", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_database_from_a_newer_version_gives_a_readable_message_and_code_2(self):
        self.home.mkdir(parents=True)
        seed = sqlite3.connect(str(self.home / "aniflow.db"))
        seed.execute("PRAGMA user_version = 99")
        seed.execute("CREATE TABLE t(a)")
        seed.commit()
        seed.close()
        result = run_python("--smoke-test", home=self.home)
        self.assertEqual(result.returncode, EXIT_DATABASE, result.stderr)
        self.assertIn("plus récente", result.stderr)
        for technical in ("Traceback", "DatabaseTooNewError", "sqlite3", "MigrationError"):
            self.assertNotIn(technical, result.stderr)

    def test_unreadable_database_is_reported_untouched_and_without_technical_text(self):
        self.home.mkdir(parents=True)
        db = self.home / "aniflow.db"
        db.write_bytes(b"ceci n'est pas une base SQLite" * 50)
        before = self.sha(db)
        result = run_python("--smoke-test", home=self.home)
        self.assertEqual(result.returncode, EXIT_DATABASE, result.stderr)
        self.assertIn("illisible", result.stderr)
        self.assertIn(str(db), result.stderr)
        for technical in ("Traceback", "not a database", "DatabaseError"):
            self.assertNotIn(technical, result.stderr)
        self.assertEqual(self.sha(db), before)

    def test_unusable_data_folder_gives_code_3(self):
        blocker = self.dir / "un-fichier"
        blocker.write_text("je ne suis pas un dossier", encoding="utf-8")
        result = run_python("--smoke-test", home=blocker / "data")
        self.assertEqual(result.returncode, EXIT_DATA_FOLDER, result.stderr)
        self.assertIn("dossier de données", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


class LaunchFlowTests(TempDirCase):
    """main() en processus, avec des doublures : codes de sortie et fermeture de la connexion SQLite."""

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(app_module, "_force_utf8_streams")  # ne pas reconfigurer les flux du lanceur de tests
        patcher.start()
        self.addCleanup(patcher.stop)
        env = mock.patch.dict(os.environ, {"ANIFLOW_HOME": str(self.home)})
        env.start()
        self.addCleanup(env.stop)
        self.connection = mock.MagicMock()
        self.context = StartupContext(AppPaths(self.home), self.connection, mock.MagicMock(), None)

    def main(self, argv, **patches):
        buffer = io.StringIO()
        with contextlib.redirect_stderr(buffer):
            code = app_module.main(argv)
        return code, buffer.getvalue()

    def test_the_connection_is_closed_after_a_normal_launch(self):
        with mock.patch.object(app_module, "run_startup_checks", return_value=self.context), mock.patch.object(app_module, "_launch", return_value=0):
            code, _ = self.main([])
        self.assertEqual(code, 0)
        self.connection.close.assert_called_once_with()

    def test_the_connection_is_closed_when_the_launch_fails(self):
        with mock.patch.object(app_module, "run_startup_checks", return_value=self.context), mock.patch.object(app_module, "_launch", side_effect=RuntimeError("boom-technique")):
            with self.assertLogs("aniflow.app", level="ERROR") as logged:
                code, message = self.main([])
        self.assertEqual(code, EXIT_UNEXPECTED)
        self.connection.close.assert_called_once_with()
        self.assertNotIn("boom-technique", message)  # rien de technique à l'écran
        self.assertIn("journal", message)
        self.assertIn("boom-technique", "\n".join(logged.output))  # le détail va au journal

    def test_a_failing_close_is_logged_and_never_changes_the_exit_code(self):
        self.connection.close.side_effect = sqlite3.ProgrammingError("fermeture impossible")
        with mock.patch.object(app_module, "run_startup_checks", return_value=self.context), mock.patch.object(app_module, "_launch", return_value=0):
            with self.assertLogs("aniflow.app", level="WARNING"):
                code, _ = self.main([])
        self.assertEqual(code, 0)

    def test_an_error_during_the_startup_checks_themselves_is_contained(self):
        with mock.patch.object(app_module, "run_startup_checks", side_effect=RuntimeError("boom-technique")):
            with self.assertLogs("aniflow.app", level="ERROR"):
                code, message = self.main(["--smoke-test"])
        self.assertEqual(code, EXIT_UNEXPECTED)
        self.assertNotIn("boom-technique", message)

    def test_smoke_mode_prints_the_failure_without_trying_to_open_a_dialog(self):
        failure = StartupFailure("Titre utile", "Message utile.", EXIT_DATABASE, "TECH-DETAIL", None)
        with mock.patch.object(app_module, "run_startup_checks", return_value=failure), mock.patch.object(
            app_module, "_qt_available", side_effect=AssertionError("Qt ne doit pas être sollicité en --smoke-test")
        ):
            code, message = self.main(["--smoke-test"])
        self.assertEqual(code, EXIT_DATABASE)
        self.assertIn("Titre utile", message)
        self.assertIn("Message utile.", message)
        self.assertNotIn("TECH-DETAIL", message)

    def test_a_startup_failure_without_pyside6_still_reports_and_returns_its_code(self):
        failure = StartupFailure("Dossier", "Message utile.", EXIT_DATA_FOLDER, "TECH-DETAIL", None)
        with mock.patch.object(app_module, "run_startup_checks", return_value=failure), mock.patch.object(app_module, "_qt_available", return_value=False):
            code, message = self.main([])
        self.assertEqual(code, EXIT_DATA_FOLDER)
        self.assertIn("Message utile.", message)
        self.assertNotIn("TECH-DETAIL", message)

    def test_missing_pyside6_gives_code_4_and_still_closes_the_connection(self):
        with mock.patch.object(app_module, "run_startup_checks", return_value=self.context), mock.patch.object(app_module, "_qt_available", return_value=False):
            code, message = self.main([])
        self.assertEqual(code, EXIT_QT_MISSING)
        self.assertIn("pip install PySide6", message)
        self.connection.close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
