import re
import unittest
from pathlib import Path

from aniflow.database.errors import SettingsError
from aniflow.database.settings import SETTINGS
from aniflow.ui.navigation import (
    DEFAULT_SECTION_ID,
    SECTION_IDS,
    SECTIONS,
    NavigationModel,
    Section,
    UnknownSectionError,
    section_by_id,
    validate_sections,
)

SPEC = Path(__file__).resolve().parents[1] / "SPEC.md"
EXPECTED_LABELS = ["Accueil / Continuer", "Recherche", "Ma bibliothèque", "Téléchargements", "Statistiques", "Paramètres"]
EXPECTED_IDS = ["accueil", "recherche", "bibliotheque", "telechargements", "statistiques", "parametres"]


def section(**overrides):
    values = {"id": "a", "label": "A", "shortcut": "Ctrl+1", "icon": "home", "delivered_in": 1}
    return Section(**{**values, **overrides})


class CatalogueTests(unittest.TestCase):
    def test_six_sections_in_the_order_of_the_spec(self):
        self.assertEqual([s.label for s in SECTIONS], EXPECTED_LABELS)

    @unittest.skipUnless(SPEC.is_file(), "SPEC.md absent")
    def test_labels_match_the_spec_section_11_line(self):
        text = SPEC.read_text(encoding="utf-8")
        found = re.search(r"Navigation principale stable : ([^\n]+?)\.\s*$", text, flags=re.M)
        self.assertIsNotNone(found, "ligne « Navigation principale stable » introuvable dans SPEC.md")
        self.assertEqual([part.strip() for part in found.group(1).split(",")], [s.label for s in SECTIONS])

    def test_ids_are_stable_because_they_are_persisted(self):
        self.assertEqual(list(SECTION_IDS), EXPECTED_IDS)
        self.assertEqual(DEFAULT_SECTION_ID, "accueil")

    def test_shortcuts_are_ctrl_1_to_6_in_order(self):
        self.assertEqual([s.shortcut for s in SECTIONS], [f"Ctrl+{n}" for n in range(1, 7)])

    def test_delivery_phase_of_each_section_follows_the_roadmap(self):
        self.assertEqual(
            {s.id: s.delivered_in for s in SECTIONS},
            {"accueil": 3, "recherche": 2, "bibliotheque": 3, "telechargements": 5, "statistiques": 4, "parametres": 1},
        )

    def test_catalogue_satisfies_its_own_invariants(self):
        validate_sections(SECTIONS)

    def test_bad_catalogues_are_rejected(self):
        bad = {
            "vide": [],
            "identifiants en double": [section(), section(shortcut="Ctrl+2")],
            "raccourcis en double": [section(), section(id="b")],
            "raccourci vide": [section(shortcut="")],
            "identifiant mal formé": [section(id="Bad Id")],
            "libellé vide": [section(label="  ")],
            "phase invalide": [section(delivered_in=0)],
        }
        for name, catalogue in bad.items():
            with self.subTest(name), self.assertRaises(ValueError):
                validate_sections(catalogue)

    def test_section_by_id(self):
        self.assertEqual(section_by_id("recherche").label, "Recherche")
        for unknown in (None, 3, "inconnue", "Accueil", ""):
            with self.subTest(unknown=unknown), self.assertRaises(UnknownSectionError) as ctx:
                section_by_id(unknown)
            self.assertIn("n'existe pas", ctx.exception.user_message)


class NavigationModelTests(unittest.TestCase):
    def test_default_and_explicit_start(self):
        self.assertEqual(NavigationModel().current.id, "accueil")
        model = NavigationModel("statistiques")
        self.assertEqual((model.current.id, model.index), ("statistiques", 4))

    def test_unknown_start_is_refused_but_a_stored_value_falls_back(self):
        with self.assertRaises(UnknownSectionError):
            NavigationModel("inconnue")
        for stored in ("inconnue", None, 3, ""):
            with self.subTest(stored=stored):
                self.assertEqual(NavigationModel.from_setting(stored).current.id, "accueil")
        self.assertEqual(NavigationModel.from_setting("parametres").current.id, "parametres")

    def test_go_to_notifies_once_with_old_and_new_section(self):
        model, events = NavigationModel(), []
        model.subscribe(lambda old, new: events.append((old.id, new.id)))
        model.go_to("recherche")
        model.go_to("recherche")  # déjà courante : aucune notification
        model.go_to("parametres")
        self.assertEqual(events, [("accueil", "recherche"), ("recherche", "parametres")])

    def test_unknown_target_raises_and_keeps_the_state(self):
        model, events = NavigationModel("recherche"), []
        model.subscribe(lambda old, new: events.append(new.id))
        with self.assertRaises(UnknownSectionError):
            model.go_to("inconnue")
        self.assertEqual((model.current.id, events), ("recherche", []))

    def test_unsubscribe_is_idempotent_and_listeners_may_unsubscribe_while_notified(self):
        model, calls = NavigationModel(), []
        stop_first = model.subscribe(lambda old, new: (calls.append("premier"), stop_first()))
        model.subscribe(lambda old, new: calls.append("second"))
        model.go_to("recherche")
        stop_first()  # deuxième désabonnement : sans effet
        model.go_to("parametres")
        self.assertEqual(calls, ["premier", "second", "second"])


class SettingIntegrationTests(unittest.TestCase):
    def test_setting_accepts_every_section_id_and_nothing_else(self):
        validate = SETTINGS["ui.last_section"].validate
        for section_id in SECTION_IDS:
            self.assertEqual(validate(section_id), section_id)
        for bad in ("inconnue", "", None, 3, ["accueil"]):
            with self.subTest(bad=bad), self.assertRaises(SettingsError):
                validate(bad)


if __name__ == "__main__":
    unittest.main()
