import logging
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from aniflow.logging_setup import setup_logging
from aniflow.paths import AppPaths, app_data_dir, logo_path, LOGO_RELATIVE_PATH
from aniflow.ui.theme import DEFAULT_PALETTE as P
from aniflow.ui.theme import Palette, build_stylesheet, contrast_ratio


class ContrastTests(unittest.TestCase):
    def test_text_pairs_meet_wcag_aa(self):
        pairs = {
            "texte/fond": (P.text, P.bg), "texte/barre latérale": (P.text, P.bg_deep), "texte/carte": (P.text, P.surface),
            "texte secondaire/fond": (P.text_muted, P.bg), "texte secondaire/carte": (P.text_muted, P.surface),
            "texte secondaire/survol": (P.text_muted, P.surface_raised), "accent clair/fond": (P.accent_soft, P.bg),
            "accent clair/carte": (P.accent_soft, P.surface), "blanc/bouton principal": (P.on_accent, P.accent),
            "blanc/bouton principal survolé": (P.on_accent, P.accent_hover), "texte/sélection": (P.text, P.accent_dim),
            "erreur/fond": (P.danger, P.bg), "succès/fond": (P.success, P.bg), "alerte/fond": (P.warning, P.bg),
        }
        for name, (fg, bg) in pairs.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(contrast_ratio(fg, bg), 4.5, name)

    def test_interface_elements_meet_3_to_1(self):
        for name, (fg, bg) in {"accent/fond": (P.accent, P.bg), "poignée de défilement/fond": (P.border_strong, P.bg)}.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(contrast_ratio(fg, bg), 3.0, name)

    def test_background_matches_the_brief(self):
        self.assertIn(P.bg_deep.upper(), {"#080D1A"})
        self.assertIn(P.bg.upper(), {"#0B1020"})

    def test_palette_values_are_hex(self):
        for name, value in vars(P).items():
            self.assertRegex(value, r"^#[0-9A-Fa-f]{6}$", name)


class StylesheetTests(unittest.TestCase):
    def test_fully_resolved(self):
        qss = build_stylesheet()
        self.assertNotIn("$", qss)
        self.assertIn(P.bg, qss)
        self.assertIn(P.accent, qss)
        self.assertIn('QPushButton[variant="primary"]', qss)
        self.assertIn(":focus", qss)  # focus clavier visible
        self.assertEqual(qss.count("{"), qss.count("}"))

    def test_custom_palette_is_applied(self):
        qss = build_stylesheet(Palette(accent="#FF00FF"))
        self.assertIn("#FF00FF", qss)


class PathsTests(unittest.TestCase):
    def test_env_override(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"ANIFLOW_HOME": tmp}):
            self.assertEqual(app_data_dir(), Path(tmp))
            paths = AppPaths.default().ensure()
            self.assertTrue(paths.backups.is_dir() and paths.logs.is_dir())
            self.assertEqual(paths.database, Path(tmp) / "aniflow.db")

    def test_logo_is_never_replaced_by_another_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIsNone(logo_path(root))
            target = root / LOGO_RELATIVE_PATH
            target.parent.mkdir(parents=True)
            target.write_bytes(b"png")
            self.assertEqual(logo_path(root), target)
        self.assertEqual(LOGO_RELATIVE_PATH.as_posix(), "docs/branding/aniflow-logo-final.png")


class LoggingTests(unittest.TestCase):
    def test_idempotent_and_writes_to_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            for _ in range(2):
                path = setup_logging(Path(tmp) / "logs")
            logger = logging.getLogger("aniflow")
            named = [h for h in logger.handlers if h.get_name() == "aniflow-file"]
            self.assertEqual(len(named), 1)
            logging.getLogger("aniflow.test").info("bonjour journal")
            named[0].flush()
            self.assertIn("bonjour journal", path.read_text(encoding="utf-8"))
            for h in named:  # libère le fichier (Windows) avant le nettoyage du dossier
                logger.removeHandler(h)
                h.close()


if __name__ == "__main__":
    unittest.main()
