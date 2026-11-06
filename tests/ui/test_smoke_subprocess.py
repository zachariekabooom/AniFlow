"""`python -m aniflow --smoke-test` lancé comme sur un PC Windows en français (processus réel, plateforme hors écran)."""

import sqlite3
import tempfile
import unittest
from pathlib import Path

from aniflow.ui.qt_logging import STYLE_MARKERS
from tests.support.qt import requires_qt
from tests.support.subproc import run_python


@requires_qt
class SmokeTestProcessTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name) / "AniFlowData"

    def test_smoke_test_exits_with_code_zero_and_says_so(self):
        result = run_python("--smoke-test", home=self.home)
        self.assertEqual(result.returncode, 0, f"stdout : {result.stdout}\nstderr : {result.stderr}")
        self.assertIn("démarrage OK", result.stdout)
        self.assertNotIn("Traceback", result.stderr)

    def test_the_journal_records_the_start_and_no_style_warning(self):
        self.assertEqual(run_python("--smoke-test", home=self.home).returncode, 0)
        journal = (self.home / "logs" / "aniflow.log").read_text(encoding="utf-8")
        self.assertIn("Smoke-test : démarrage OK", journal)
        for marker in STYLE_MARKERS:
            self.assertNotIn(marker, journal)

    def test_a_second_start_reuses_the_same_data_and_still_succeeds(self):
        for _ in range(2):
            self.assertEqual(run_python("--smoke-test", home=self.home).returncode, 0)
        self.assertTrue((self.home / "aniflow.db").is_file())

    def test_the_smoke_test_stores_no_preference(self):
        self.assertEqual(run_python("--smoke-test", home=self.home).returncode, 0)
        connection = sqlite3.connect(str(self.home / "aniflow.db"))
        try:
            keys = [row[0] for row in connection.execute("SELECT key FROM settings")]
        finally:
            connection.close()
        self.assertEqual(keys, [])


if __name__ == "__main__":
    unittest.main()
