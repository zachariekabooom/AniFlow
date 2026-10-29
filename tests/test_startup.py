import hashlib
import logging
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aniflow.database import LATEST_VERSION, MigrationError, current_version, list_backups
from aniflow.paths import AppPaths
from tests.support.openfiles import assert_released_then_delete, without_garbage_collector
from aniflow.startup import (
    EXIT_DATA_FOLDER,
    EXIT_DATABASE,
    EXIT_UNEXPECTED,
    StartupContext,
    StartupFailure,
    run_startup_checks,
)


def remove_file_handlers():
    logger = logging.getLogger("aniflow")
    for handler in list(logger.handlers):
        if handler.get_name() == "aniflow-file":
            logger.removeHandler(handler)
            handler.close()


class StartupCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.paths = AppPaths(self.dir / "AniFlowData")

    def start(self, paths=None, **kwargs):
        kwargs.setdefault("configure_logging", False)
        result = run_startup_checks(paths or self.paths, **kwargs)
        if isinstance(result, StartupContext):
            self.addCleanup(result.connection.close)
        return result

    def sha(self, path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class HealthyStartTests(StartupCase):
    def test_first_start_creates_and_migrates_everything(self):
        ctx = self.start()
        self.assertIsInstance(ctx, StartupContext)
        self.assertTrue(self.paths.database.is_file() and self.paths.backups.is_dir() and self.paths.logs.is_dir())
        self.assertEqual(current_version(ctx.connection), LATEST_VERSION)
        self.assertEqual(ctx.settings.get("ui.last_section"), "accueil")
        self.assertEqual(list_backups(self.paths.backups), [])  # base neuve : rien à sauvegarder

    def test_second_start_reuses_the_database_and_takes_no_backup(self):
        first = self.start()
        first.settings.set("ui.last_section", "recherche")
        first.connection.close()
        second = self.start()
        self.assertIsInstance(second, StartupContext)
        self.assertEqual(second.settings.get("ui.last_section"), "recherche")
        self.assertEqual(list_backups(self.paths.backups), [])

    def test_logging_is_configured_on_request(self):
        self.addCleanup(remove_file_handlers)
        ctx = self.start(configure_logging=True)
        self.assertEqual(ctx.log_path, self.paths.logs / "aniflow.log")
        self.assertTrue(ctx.log_path.is_file())


class DatabaseFailureTests(StartupCase):
    def setUp(self):
        super().setUp()
        without_garbage_collector(self)  # aucune connexion ne doit dépendre du ramasse-miettes (WinError 32 sous Windows)

    def seed_database(self, user_version=None, content=None):
        self.paths.ensure()
        if content is not None:
            self.paths.database.write_bytes(content)
            return
        conn = sqlite3.connect(str(self.paths.database))
        conn.execute(f"PRAGMA user_version = {user_version}")
        conn.execute("CREATE TABLE t(a)")
        conn.commit()
        conn.close()

    def test_database_from_a_newer_version(self):
        self.seed_database(user_version=99)
        failure = self.start()
        self.assertIsInstance(failure, StartupFailure)
        self.assertEqual((failure.exit_code, failure.title), (EXIT_DATABASE, "Base de données plus récente"))
        self.assertIn("plus récente", failure.user_message)
        self.assertIn("99", failure.technical)
        check = sqlite3.connect(str(self.paths.database))
        self.addCleanup(check.close)
        self.assertEqual(check.execute("PRAGMA user_version").fetchone()[0], 99)  # jamais « migrée » vers le bas
        check.close()
        assert_released_then_delete(self, self.paths.database)  # Windows : échouerait si une connexion restait ouverte

    def test_unreadable_database_is_reported_and_left_untouched(self):
        self.seed_database(content=b"ceci n'est pas une base SQLite" * 50)
        before = self.sha(self.paths.database)
        failure = self.start()
        self.assertIsInstance(failure, StartupFailure)
        self.assertEqual((failure.exit_code, failure.title), (EXIT_DATABASE, "Base de données illisible"))
        self.assertIn(str(self.paths.database), failure.user_message)
        self.assertIn(str(self.paths.backups), failure.user_message)
        self.assertIn("pas tenté de le réparer", failure.user_message)
        self.assertEqual(self.sha(self.paths.database), before)
        assert_released_then_delete(self, self.paths.database)  # c'est ici que Windows signalait WinError 32

    def test_migration_failure(self):
        with mock.patch("aniflow.startup.open_app_database", side_effect=MigrationError(2, "boom")):
            failure = self.start()
        self.assertEqual((failure.exit_code, failure.title), (EXIT_DATABASE, "Mise à jour de la base impossible"))
        self.assertIn("annulée", failure.user_message)


class FolderFailureTests(StartupCase):
    def test_data_folder_that_cannot_be_created(self):
        blocker = self.dir / "un-fichier"
        blocker.write_text("je ne suis pas un dossier", encoding="utf-8")
        paths = AppPaths(blocker / "data")
        failure = self.start(paths)
        self.assertIsInstance(failure, StartupFailure)
        self.assertEqual((failure.exit_code, failure.title), (EXIT_DATA_FOLDER, "Dossier de données inaccessible"))
        self.assertIn(str(paths.root), failure.user_message)

    def test_os_errors_while_opening_are_folder_problems(self):
        errors = [PermissionError(13, "Accès refusé"), sqlite3.OperationalError("unable to open database file")]
        for error in errors:
            with self.subTest(type(error).__name__), mock.patch("aniflow.startup.open_app_database", side_effect=error):
                failure = self.start()
                self.assertEqual(failure.exit_code, EXIT_DATA_FOLDER)
                self.assertIn(str(self.paths.root), failure.user_message)


class UnexpectedFailureTests(StartupCase):
    def test_other_sqlite_operational_errors_are_unexpected(self):
        with mock.patch("aniflow.startup.open_app_database", side_effect=sqlite3.OperationalError("disk I/O error")):
            failure = self.start()
        self.assertEqual((failure.exit_code, failure.title), (EXIT_UNEXPECTED, "Démarrage impossible"))

    def test_unexpected_error_stays_out_of_the_message_but_goes_to_the_log(self):
        with mock.patch("aniflow.startup.open_app_database", side_effect=RuntimeError("boom-technique")):
            with self.assertLogs("aniflow.startup", level="ERROR") as captured:
                failure = self.start()
        self.assertEqual(failure.exit_code, EXIT_UNEXPECTED)
        self.assertNotIn("boom-technique", failure.user_message)
        self.assertIn("boom-technique", failure.technical)
        self.assertIn("boom-technique", "\n".join(captured.output))

    def test_message_names_the_log_file_when_logging_is_configured(self):
        self.addCleanup(remove_file_handlers)
        with mock.patch("aniflow.startup.open_app_database", side_effect=RuntimeError("boom-technique")):
            failure = self.start(configure_logging=True)
        self.assertEqual(failure.log_path, self.paths.logs / "aniflow.log")
        self.assertIn(str(failure.log_path), failure.user_message)
        for handler in logging.getLogger("aniflow").handlers:
            handler.flush()
        content = failure.log_path.read_text(encoding="utf-8")
        self.assertIn("boom-technique", content)
        self.assertIn("Traceback", content)


if __name__ == "__main__":
    unittest.main()
