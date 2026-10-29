import base64
import hashlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aniflow.database import (
    LATEST_VERSION,
    MIGRATIONS,
    DatabaseCorruptError,
    DatabaseRestoreError,
    DatabaseTooNewError,
    Migration,
    MigrationError,
    SettingsError,
    SettingsStore,
    SqliteResponseCache,
    backup_database,
    connect,
    current_version,
    list_backups,
    migrate,
    open_app_database,
    restore_database,
    verify_database_file,
)
from aniflow.paths import AppPaths
from aniflow.ui.navigation import SECTION_IDS
from tests.support.fake_mpv import FakeClock
from tests.support.openfiles import assert_released_then_delete, without_garbage_collector


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)
        self.db_path = self.dir / "aniflow.db"
        self.backups = self.dir / "backups"

    def open(self):
        conn = connect(self.db_path)
        self.addCleanup(conn.close)
        return conn

    def tables(self, conn):
        return {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


class MigrationTests(TempDirCase):
    def test_fresh_database_is_migrated_and_idempotent(self):
        conn = self.open()
        self.assertEqual(migrate(conn, backups_dir=self.backups), [1])
        self.assertEqual(current_version(conn), LATEST_VERSION)
        self.assertLessEqual({"settings", "http_cache"}, self.tables(conn))
        self.assertEqual(migrate(conn, backups_dir=self.backups), [])
        self.assertEqual(list_backups(self.backups), [])  # base neuve : rien à sauvegarder

    def test_failed_migration_is_rolled_back_completely(self):
        conn = self.open()
        migrate(conn)
        broken = MIGRATIONS + (Migration(2, "cassée", "CREATE TABLE partiel(a); CREATE TABLE partiel(a);"),)
        with self.assertRaises(MigrationError) as ctx:
            migrate(conn, backups_dir=self.backups, migrations=broken)
        self.assertEqual(ctx.exception.version, 2)
        self.assertEqual(current_version(conn), 1)
        self.assertNotIn("partiel", self.tables(conn))  # atomique : pas de table à moitié créée
        self.assertFalse(conn.in_transaction)

    def test_backup_is_taken_before_upgrading_an_existing_database(self):
        conn = self.open()
        migrate(conn)
        SettingsStore(conn).set("ui.title_language", "english")
        upgraded = MIGRATIONS + (Migration(2, "ajout", "CREATE TABLE works(id INTEGER PRIMARY KEY);"),)
        self.assertEqual(migrate(conn, backups_dir=self.backups, migrations=upgraded), [2])
        backups = list_backups(self.backups)
        self.assertEqual([b.tag for b in backups], ["pre-migration-v1"])
        self.assertEqual(verify_database_file(backups[0].path), 1)
        self.assertIn("works", self.tables(conn))

    def test_database_from_newer_version_is_refused(self):
        conn = self.open()
        conn.execute("PRAGMA user_version = 99")
        with self.assertRaises(DatabaseTooNewError) as ctx:
            migrate(conn)
        self.assertIn("plus récente", ctx.exception.user_message)

    def test_migrations_must_be_consecutive(self):
        with self.assertRaises(ValueError):
            migrate(self.open(), migrations=(Migration(1, "a", "SELECT 1;"), Migration(3, "c", "SELECT 1;")))


class BackupRestoreTests(TempDirCase):
    def prepared(self):
        conn = self.open()
        migrate(conn)
        settings = SettingsStore(conn)
        settings.set("ui.title_language", "english")
        return conn, settings

    def test_backup_is_a_single_verified_file(self):
        conn, _ = self.prepared()
        path = backup_database(conn, self.backups, tag="manuel test!")
        self.assertEqual(verify_database_file(path), 1)
        self.assertEqual(sorted(p.name for p in self.backups.iterdir()), [path.name])  # ni -wal, ni -shm, ni .part
        self.assertEqual(list_backups(self.backups)[0].tag, "manuel-test")

    def test_restore_roundtrip_keeps_a_safety_copy_of_the_current_database(self):
        conn, settings = self.prepared()
        good = backup_database(conn, self.backups)
        settings.set("ui.title_language", "native")
        conn.close()
        stale = [Path(str(self.db_path) + suffix) for suffix in ("-wal", "-shm")]
        for leftover in stale:  # journaux périmés de l'ancienne base : ils corrompraient la base restaurée
            leftover.write_bytes(b"journal perime")
        safety = restore_database(good, self.db_path, self.backups)
        self.assertFalse(any(leftover.exists() for leftover in stale))
        restored = self.open()
        self.assertEqual(SettingsStore(restored).get("ui.title_language"), "english")
        safety_conn = sqlite3.connect(str(safety))
        self.addCleanup(safety_conn.close)
        self.assertEqual(safety_conn.execute("SELECT value FROM settings WHERE key='ui.title_language'").fetchone()[0], '"native"')

    def test_corrupt_backup_is_refused_and_live_database_is_untouched(self):
        conn, settings = self.prepared()
        conn.close()
        garbage = self.dir / "garbage.db"
        garbage.write_bytes(b"ceci n'est pas une base SQLite" * 50)
        with self.assertRaises(DatabaseCorruptError):
            restore_database(garbage, self.db_path, self.backups)
        reopened = self.open()
        self.assertEqual(SettingsStore(reopened).get("ui.title_language"), "english")

    def test_missing_backup_is_refused(self):
        with self.assertRaises(DatabaseRestoreError) as ctx:
            restore_database(self.dir / "absent.db", self.db_path, self.backups)
        self.assertIn("introuvable", ctx.exception.user_message)

    def test_backup_from_newer_version_is_refused(self):
        newer = sqlite3.connect(str(self.dir / "newer.db"))
        newer.execute("PRAGMA user_version = 99")
        newer.execute("CREATE TABLE t(a)")
        newer.commit()
        newer.close()
        with self.assertRaises(DatabaseTooNewError):
            restore_database(self.dir / "newer.db", self.db_path, self.backups)

    def test_list_backups_ignores_foreign_files(self):
        conn, _ = self.prepared()
        backup_database(conn, self.backups, tag="a")
        (self.backups / "notes.txt").write_text("x")
        (self.backups / "aniflow-pas-un-format.db").write_text("x")
        self.assertEqual([b.tag for b in list_backups(self.backups)], ["a"])


class SettingsTests(TempDirCase):
    def store(self):
        conn = self.open()
        migrate(conn)
        return conn, SettingsStore(conn)

    def test_defaults_roundtrip_reset(self):
        _, s = self.store()
        self.assertEqual(s.get("ai.ollama_url"), "http://127.0.0.1:11434")
        self.assertIsNone(s.get("ai.model"))
        self.assertIs(s.get("anilist.include_adult"), False)
        s.set("ai.model", " gemma4:e2b ")
        self.assertEqual(s.get("ai.model"), "gemma4:e2b")
        s.reset("ai.model")
        self.assertIsNone(s.get("ai.model"))
        self.assertEqual(
            set(s.all()),
            {"ai.ollama_url", "ai.model", "anilist.include_adult", "ui.title_language", "ui.last_section", "ui.window_geometry", "downloads.dir"},
        )

    def test_values_persist_across_connections(self):
        conn, s = self.store()
        s.set("downloads.dir", "D:\\Animés")
        conn.close()
        self.assertEqual(SettingsStore(self.open()).get("downloads.dir"), "D:\\Animés")

    def test_local_only_policy_is_enforced_at_configuration_time(self):
        _, s = self.store()
        for url in ("https://api.openai.com", "http://192.168.0.5:11434", "http://example.org"):
            with self.subTest(url=url), self.assertRaises(SettingsError):
                s.set("ai.ollama_url", url)
        for model in ("gpt-oss:120b-cloud", "x:cloud"):
            with self.subTest(model=model), self.assertRaises(SettingsError):
                s.set("ai.model", model)
        self.assertEqual(s.get("ai.ollama_url"), "http://127.0.0.1:11434")  # inchangé après refus
        self.assertEqual(s.set("ai.ollama_url", "http://localhost:11434/"), "http://localhost:11434")

    def test_last_section_and_window_geometry_persist(self):
        conn, s = self.store()
        self.assertEqual(s.get("ui.last_section"), "accueil")
        self.assertIsNone(s.get("ui.window_geometry"))
        for section_id in SECTION_IDS:
            self.assertEqual(s.set("ui.last_section", section_id), section_id)
        geometry = base64.b64encode(bytes(range(100))).decode("ascii")
        s.set("ui.last_section", "recherche")
        s.set("ui.window_geometry", geometry)
        conn.close()
        reopened = SettingsStore(self.open())
        self.assertEqual((reopened.get("ui.last_section"), reopened.get("ui.window_geometry")), ("recherche", geometry))
        reopened.set("ui.window_geometry", None)
        self.assertIsNone(reopened.get("ui.window_geometry"))

    def test_invalid_section_and_geometry_are_refused_and_nothing_is_stored(self):
        _, s = self.store()
        for bad in ("inconnue", "", None, 3, ["accueil"], "Accueil"):
            with self.subTest(section=bad), self.assertRaises(SettingsError) as ctx:
                s.set("ui.last_section", bad)
            self.assertIn("n'existe pas", ctx.exception.user_message)
        too_big = base64.b64encode(b"x" * 5000).decode("ascii")
        for bad in ("pas du base64 !!", "", 3, "é", too_big, ["QUJD"]):
            with self.subTest(geometry=bad), self.assertRaises(SettingsError) as ctx:
                s.set("ui.window_geometry", bad)
            self.assertIn("invalide", ctx.exception.user_message)
        self.assertEqual(s.get("ui.last_section"), "accueil")
        self.assertIsNone(s.get("ui.window_geometry"))

    def test_unknown_keys_and_bad_values(self):
        _, s = self.store()
        with self.assertRaises(SettingsError):
            s.get("ai.cloud_fallback")
        with self.assertRaises(SettingsError):
            s.set("anilist.include_adult", "oui")
        with self.assertRaises(SettingsError):
            s.set("ui.title_language", "klingon")
        with self.assertRaises(SettingsError):
            s.set("ai.model", "   ")


class HttpCacheTests(TempDirCase):
    def test_ttl_expiry_persistence_and_purge(self):
        clock = FakeClock()
        conn = self.open()
        migrate(conn)
        cache = SqliteResponseCache(conn, clock=clock.time)
        cache.set("k", {"données": [1, 2, 3]}, ttl=100)
        self.assertEqual(cache.get("k"), {"données": [1, 2, 3]})
        conn.close()
        cache = SqliteResponseCache(self.open(), clock=clock.time)  # survit à la fermeture de la base
        self.assertEqual(cache.get("k"), {"données": [1, 2, 3]})
        clock.sleep(101)
        self.assertIsNone(cache.get("k"))
        cache.set("a", 1, ttl=1)
        cache.set("b", 2, ttl=1000)
        clock.sleep(5)
        self.assertEqual(cache.purge_expired(), 1)
        self.assertEqual(cache.get("b"), 2)

    def test_overwrite(self):
        conn = self.open()
        migrate(conn)
        cache = SqliteResponseCache(conn)
        cache.set("k", 1, 100)
        cache.set("k", 2, 100)
        self.assertEqual(cache.get("k"), 2)


class BootstrapTests(TempDirCase):
    def test_open_app_database_creates_everything(self):
        paths = AppPaths(self.dir / "AniFlowData")
        conn = open_app_database(paths)
        self.addCleanup(conn.close)
        self.assertTrue(paths.database.is_file() and paths.backups.is_dir() and paths.logs.is_dir())
        self.assertEqual(current_version(conn), LATEST_VERSION)

    def test_open_app_database_closes_connection_on_failure(self):
        paths = AppPaths(self.dir / "AniFlowData").ensure()
        pre = sqlite3.connect(str(paths.database))
        pre.execute("PRAGMA user_version = 99")
        pre.execute("CREATE TABLE t(a)")
        pre.commit()
        pre.close()
        with self.assertRaises(DatabaseTooNewError):
            open_app_database(paths)


class ConnectionCleanupTests(TempDirCase):
    """Aucune connexion ne doit dépendre du ramasse-miettes pour être fermée.

    Python ≥ 3.11 : une Connection abandonnée n'est libérée que par le ramasse-miettes cyclique ; sous Windows, un
    fichier resté ouvert bloque la suppression du dossier temporaire (WinError 32).
    """

    def setUp(self):
        super().setUp()
        without_garbage_collector(self)

    def unreadable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"ceci n'est pas une base SQLite" * 50)
        return path

    def test_connection_is_closed_when_a_pragma_fails(self):
        fake = mock.MagicMock()
        fake.execute.side_effect = [None, None, sqlite3.DatabaseError("file is not a database")]  # 3e PRAGMA : journal_mode
        with mock.patch("aniflow.database.connection.sqlite3.connect", return_value=fake):
            with self.assertRaises(sqlite3.DatabaseError):
                connect(self.dir / "x.db")
        fake.close.assert_called_once_with()

    def test_original_error_wins_when_closing_also_fails(self):
        fake = mock.MagicMock()
        fake.execute.side_effect = sqlite3.DatabaseError("file is not a database")
        fake.close.side_effect = sqlite3.ProgrammingError("fermeture impossible")
        with mock.patch("aniflow.database.connection.sqlite3.connect", return_value=fake):
            with self.assertRaises(sqlite3.DatabaseError) as ctx:
                connect(self.dir / "x.db")
        self.assertIn("not a database", str(ctx.exception))

    def test_unreadable_file_is_released_as_soon_as_connect_fails(self):
        path = self.unreadable(self.dir / "illisible.db")
        with self.assertRaises(sqlite3.DatabaseError):
            connect(path)
        assert_released_then_delete(self, path)

    def test_open_app_database_releases_and_leaves_untouched_an_unreadable_file(self):
        paths = AppPaths(self.dir / "AniFlowData").ensure()
        self.unreadable(paths.database)
        before = hashlib.sha256(paths.database.read_bytes()).hexdigest()
        with self.assertRaises(sqlite3.DatabaseError) as ctx:
            open_app_database(paths)
        self.assertIn("not a database", str(ctx.exception))  # message d'erreur inchangé
        self.assertEqual(hashlib.sha256(paths.database.read_bytes()).hexdigest(), before)
        assert_released_then_delete(self, paths.database)

    def test_open_app_database_releases_the_file_when_a_migration_fails(self):
        paths = AppPaths(self.dir / "AniFlowData")
        with mock.patch("aniflow.database.bootstrap.migrate", side_effect=MigrationError(2, "boom")):
            with self.assertRaises(MigrationError) as ctx:
                open_app_database(paths)
        self.assertIn("annulée", ctx.exception.user_message)  # message d'erreur inchangé
        assert_released_then_delete(self, paths.database)

    def test_original_migration_error_wins_when_closing_also_fails(self):
        fake = mock.MagicMock()
        fake.close.side_effect = sqlite3.ProgrammingError("fermeture impossible")
        with mock.patch("aniflow.database.bootstrap.connect", return_value=fake), mock.patch(
            "aniflow.database.bootstrap.migrate", side_effect=MigrationError(2, "boom")
        ):
            with self.assertRaises(MigrationError):
                open_app_database(AppPaths(self.dir / "AniFlowData"))
        fake.close.assert_called_once_with()

    def test_connect_keeps_its_normal_behaviour_when_opening_succeeds(self):
        conn = connect(self.dir / "ok.db")
        self.addCleanup(conn.close)
        self.assertIs(conn.row_factory, sqlite3.Row)
        self.assertIsNone(conn.isolation_level)
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(conn.execute("PRAGMA busy_timeout").fetchone()[0], 5000)
        self.assertEqual(conn.execute("PRAGMA synchronous").fetchone()[0], 1)  # NORMAL
        conn.execute("CREATE TABLE t(a)")
        conn.execute("INSERT INTO t VALUES (1)")
        self.assertEqual(conn.execute("SELECT a FROM t").fetchone()["a"], 1)  # lignes accessibles par nom


if __name__ == "__main__":
    unittest.main()
