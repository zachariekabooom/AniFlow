import sqlite3
import tempfile
import unittest
from pathlib import Path

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
from tests.support.fake_mpv import FakeClock


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
        self.assertEqual(set(s.all()), {"ai.ollama_url", "ai.model", "anilist.include_adult", "ui.title_language", "downloads.dir"})

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


if __name__ == "__main__":
    unittest.main()
