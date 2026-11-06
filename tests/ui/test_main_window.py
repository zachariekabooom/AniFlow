"""Fenêtre principale, barre latérale et pages (PySide6, plateforme « offscreen » par défaut).

Ces tests sont ignorés si PySide6 est absent. Les parties qui dépendent de l'activation d'une fenêtre (touches
Ctrl+chiffre réellement pressées) sont ignorées — et non en échec — quand l'environnement ne peut pas activer de fenêtre.
"""

import base64
import tempfile
import unittest
from pathlib import Path

from aniflow.paths import AppPaths
from aniflow.startup import StartupContext, run_startup_checks
from aniflow.ui.navigation import SECTIONS
from tests.support.qt import HAS_QT, requires_qt

if HAS_QT:
    from PySide6.QtCore import QByteArray, QSize, Qt, QThreadPool
    from PySide6.QtGui import QPixmap
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QAbstractButton, QComboBox, QLabel, QLineEdit
    from aniflow.ui.application import create_application
    from aniflow.ui.main_window import DEFAULT_HEIGHT, DEFAULT_WIDTH, MIN_HEIGHT, MIN_WIDTH, MainWindow

EXPECTED_LABELS = ["Accueil / Continuer", "Recherche", "Ma bibliothèque", "Téléchargements", "Statistiques", "Paramètres"]
EXPECTED_IDS = ["accueil", "recherche", "bibliotheque", "telechargements", "statistiques", "parametres"]


@requires_qt
class WindowCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()  # QApplication partagée, thème appliqué

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        started = run_startup_checks(AppPaths(self.dir / "AniFlowData"), configure_logging=False)
        self.assertIsInstance(started, StartupContext, getattr(started, "user_message", started))
        self.addCleanup(started.connection.close)  # enregistré avant la fenêtre : fermé APRÈS elle (la fermeture écrit des préférences)
        self.settings, self.connection = started.settings, started.connection

    def make_window(self, **kwargs):
        window = MainWindow(self.settings, **kwargs)
        self.addCleanup(self.dispose, window)
        return window

    def shown_window(self, **kwargs):
        window = self.make_window(**kwargs)
        window.show()
        self.app.processEvents()
        return window

    def dispose(self, window):
        window.close()
        window.deleteLater()
        self.app.processEvents()

    def store_raw(self, key, json_text):
        """Écrit une valeur brute en base, en contournant la validation (base modifiée à la main, version future…)."""
        self.connection.execute("INSERT OR REPLACE INTO settings(key, value, updated_at) VALUES (?, ?, 'test')", (key, json_text))

    def click(self, window, section_id):
        QTest.mouseClick(window.sidebar.buttons[section_id], Qt.MouseButton.LeftButton)
        self.app.processEvents()


@requires_qt
class NavigationTests(WindowCase):
    def test_six_entries_in_the_exact_order_with_one_page_each(self):
        window = self.make_window()
        self.assertEqual([b.text() for b in window.sidebar.buttons.values()], EXPECTED_LABELS)
        self.assertEqual(list(window.sidebar.buttons), EXPECTED_IDS)
        self.assertEqual(window.stack.count(), 6)
        self.assertEqual(list(window.pages), EXPECTED_IDS)

    def test_the_first_section_is_shown_and_marked_active_by_default(self):
        window = self.make_window()
        self.assertEqual((window.navigation.current.id, window.stack.currentIndex()), ("accueil", 0))
        self.assertTrue(window.sidebar.buttons["accueil"].isChecked())
        self.assertEqual(window.windowTitle(), "AniFlow — Accueil / Continuer")

    def test_clicking_an_entry_opens_its_page_and_marks_only_it_active(self):
        window = self.shown_window()
        for index, section in enumerate(SECTIONS):
            with self.subTest(section.id):
                self.click(window, section.id)
                self.assertEqual((window.navigation.current.id, window.stack.currentIndex()), (section.id, index))
                self.assertEqual([sid for sid, b in window.sidebar.buttons.items() if b.isChecked()], [section.id])
                self.assertIn(section.label, window.windowTitle())

    def test_return_and_space_activate_the_focused_entry(self):
        window = self.shown_window()
        QTest.keyClick(window.sidebar.buttons["recherche"], Qt.Key.Key_Return)
        self.assertEqual(window.navigation.current.id, "recherche")
        QTest.keyClick(window.sidebar.buttons["statistiques"], Qt.Key.Key_Space)
        self.assertEqual(window.navigation.current.id, "statistiques")
        QTest.keyClick(window.sidebar.buttons["bibliotheque"], Qt.Key.Key_Enter)  # touche Entrée du pavé numérique
        self.assertEqual(window.navigation.current.id, "bibliotheque")

    def test_the_six_shortcuts_are_declared_and_navigate(self):
        window = self.make_window()
        self.assertEqual([s.key().toString() for s in window.shortcuts], [f"Ctrl+{n}" for n in range(1, 7)])
        for index, shortcut in enumerate(window.shortcuts):
            with self.subTest(shortcut=shortcut.key().toString()):
                shortcut.activated.emit()
                self.assertEqual((window.navigation.index, window.stack.currentIndex()), (index, index))

    def test_ctrl_digit_key_presses_navigate_when_the_window_can_be_activated(self):
        window = self.shown_window()
        window.activateWindow()
        if not QTest.qWaitForWindowActive(window, 2000):
            self.skipTest("fenêtre non activable dans cet environnement : les raccourcis déclarés sont couverts par un autre test")
        for digit, key in enumerate((Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4, Qt.Key.Key_5, Qt.Key.Key_6)):
            with self.subTest(digit=digit + 1):
                QTest.keyClick(window, key, Qt.KeyboardModifier.ControlModifier)
                self.assertEqual(window.navigation.index, digit)

    def test_tab_order_follows_the_sidebar_and_every_entry_can_take_focus(self):
        window = self.make_window()
        buttons = list(window.sidebar.buttons.values())
        for button in buttons:
            self.assertEqual(button.focusPolicy(), Qt.FocusPolicy.StrongFocus)
        for first, second in zip(buttons, buttons[1:]):
            self.assertIs(first.nextInFocusChain(), second)

    def test_accessible_names_and_tooltips(self):
        window = self.make_window()
        for section in SECTIONS:
            button = window.sidebar.buttons[section.id]
            self.assertEqual(button.accessibleName(), section.label)
            self.assertIn(section.shortcut, button.toolTip())
            self.assertEqual(window.pages[section.id].accessibleName(), section.label)
        self.assertEqual(window.sidebar.accessibleName(), "Navigation principale")


@requires_qt
class HonestPagesTests(WindowCase):
    def test_pages_not_delivered_say_so_and_offer_no_control(self):
        window = self.make_window()
        for section_id, page in window.pages.items():
            with self.subTest(section_id):
                for control in (QAbstractButton, QLineEdit, QComboBox):
                    self.assertEqual(page.findChildren(control), [], f"{control.__name__} sur une page non livrée")
                texts = " ".join(label.text() for label in page.findChildren(QLabel))
                self.assertIn("pas encore disponible", texts)

    def test_no_background_thread_is_started_by_the_window(self):
        window = self.shown_window()
        self.click(window, "recherche")
        self.assertEqual(QThreadPool.globalInstance().activeThreadCount(), 0)


@requires_qt
class PersistenceTests(WindowCase):
    def test_the_last_section_is_saved_at_once_and_restored(self):
        window = self.make_window()
        window.navigation.go_to("statistiques")
        self.assertEqual(self.settings.get("ui.last_section"), "statistiques")
        again = self.make_window()
        self.assertEqual((again.navigation.current.id, again.stack.currentIndex()), ("statistiques", 4))
        self.assertTrue(again.sidebar.buttons["statistiques"].isChecked())

    def test_the_geometry_is_saved_when_the_window_closes_and_can_be_restored(self):
        window = self.shown_window()
        window.close()
        stored = self.settings.get("ui.window_geometry")
        raw = base64.b64decode(stored, validate=True)
        self.assertGreater(len(raw), 0)
        other = self.make_window()
        self.assertTrue(other.restoreGeometry(QByteArray(raw)))

    def test_an_invalid_geometry_is_ignored_without_failing_the_startup(self):
        invalid = {
            "octets qui ne sont pas une géométrie Qt": '"%s"' % base64.b64encode(b"pas une geometrie Qt").decode("ascii"),
            "base64 invalide": '"!!! pas du base64 !!!"',
            "mauvais type": "3",
            "valeur nulle": "null",
        }
        for name, json_text in invalid.items():
            with self.subTest(name):
                self.store_raw("ui.window_geometry", json_text)
                window = self.make_window()  # ne doit pas lever
                self.assertGreaterEqual(window.width(), MIN_WIDTH)
                self.assertGreaterEqual(window.height(), MIN_HEIGHT)
                self.assertEqual(window.navigation.current.id, "accueil")

    def test_an_unknown_or_malformed_stored_section_falls_back_to_the_first(self):
        for json_text in ('"inconnue"', "12", "null", '"Accueil"'):
            with self.subTest(json_text):
                self.store_raw("ui.last_section", json_text)
                self.assertEqual(self.make_window().navigation.current.id, "accueil")

    def test_persist_false_reads_preferences_but_writes_nothing(self):
        self.settings.set("ui.last_section", "recherche")
        window = self.make_window(persist=False)
        self.assertEqual(window.navigation.current.id, "recherche")  # lecture normale
        window.navigation.go_to("telechargements")
        window.close()
        self.assertEqual(self.settings.get("ui.last_section"), "recherche")
        self.assertIsNone(self.settings.get("ui.window_geometry"))

    def test_the_window_works_without_any_settings_store(self):
        window = MainWindow(None)
        self.addCleanup(self.dispose, window)
        window.sidebar.buttons["parametres"].click()
        self.assertEqual(window.navigation.current.id, "parametres")
        window.close()  # ne doit pas lever


@requires_qt
class SizeAndLogoTests(WindowCase):
    def test_the_minimum_size_is_enforced(self):
        window = self.make_window()
        self.assertEqual(window.minimumSize(), QSize(MIN_WIDTH, MIN_HEIGHT))
        window.resize(200, 200)
        self.assertGreaterEqual(window.width(), MIN_WIDTH)
        self.assertGreaterEqual(window.height(), MIN_HEIGHT)
        self.assertEqual((MIN_WIDTH, MIN_HEIGHT), (960, 600))

    def test_a_default_size_is_used_without_stored_geometry(self):
        window = self.make_window()
        self.assertGreaterEqual(window.width(), MIN_WIDTH)
        self.assertEqual((DEFAULT_WIDTH, DEFAULT_HEIGHT), (1280, 800))

    def test_the_logo_is_shown_only_when_the_file_exists_and_can_be_read(self):
        good = self.dir / "logo.png"
        pixmap = QPixmap(80, 40)
        pixmap.fill(Qt.GlobalColor.darkBlue)
        self.assertTrue(pixmap.save(str(good), "PNG"))
        not_an_image = self.dir / "faux.png"
        not_an_image.write_text("ceci n'est pas une image", encoding="utf-8")
        cases = (("aucun fichier", None, False), ("fichier introuvable", self.dir / "absent.png", False), ("fichier illisible", not_an_image, False), ("logo valide", good, True))
        for name, logo, shown in cases:
            with self.subTest(name):
                window = self.make_window(logo=logo)
                self.assertEqual(window.sidebar.logo_label is not None, shown)
                if shown:
                    self.assertFalse(window.sidebar.logo_label.pixmap().isNull())


if __name__ == "__main__":
    unittest.main()
