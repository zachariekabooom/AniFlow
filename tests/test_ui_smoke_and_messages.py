import unittest

from aniflow.ui.navigation import SECTIONS
from aniflow.ui.pages.messages import IN_PROGRESS_PHASE, placeholder_message
from aniflow.ui.smoke import SmokeFacts, smoke_problems
from aniflow.ui.theme import DEFAULT_PALETTE, Palette, contrast_ratio, relative_luminance
from aniflow.ui.theme.qt_palette import DISABLED_ROLE_TOKENS, ROLE_TOKENS

HEALTHY = SmokeFacts(window_visible=True, sections_shown=6, sections_expected=6, navigation_in_sync=True, theme_applied=True, lc_numeric="C", base_style="fusion")


def facts(**changes):
    return SmokeFacts(**{**HEALTHY.__dict__, **changes})


class SmokeProblemsTests(unittest.TestCase):
    def test_healthy_start_has_no_problem(self):
        self.assertEqual(smoke_problems(HEALTHY), [])

    def test_each_failure_is_reported_in_french(self):
        cases = {
            "fenêtre invisible": (facts(window_visible=False), "n'est pas visible"),
            "pages manquantes": (facts(sections_shown=4), "4 page(s)"),
            "navigation désynchronisée": (facts(navigation_in_sync=False), "ne correspond pas"),
            "thème absent": (facts(theme_applied=False), "thème sombre"),
            "locale numérique": (facts(lc_numeric="fr_FR"), "LC_NUMERIC vaut « fr_FR »"),
            "style de base autre que Fusion": (facts(base_style="windows11"), "n'est pas Fusion (obtenu : « windows11 »)"),
            "style de base inconnu": (facts(base_style=""), "obtenu : « inconnu »"),
            "avertissement de style": (facts(style_warnings=("Could not parse application stylesheet",)), "avertissement de style Qt : Could not parse"),
        }
        for name, (case, fragment) in cases.items():
            with self.subTest(name):
                problems = smoke_problems(case)
                self.assertEqual(len(problems), 1, problems)
                self.assertIn(fragment, problems[0])

    def test_problems_accumulate(self):
        self.assertEqual(len(smoke_problems(facts(window_visible=False, theme_applied=False, lc_numeric="fr_FR"))), 3)


class PlaceholderMessageTests(unittest.TestCase):
    def test_every_section_gets_an_honest_message(self):
        for section in SECTIONS:
            with self.subTest(section.id):
                headline, detail = placeholder_message(section)
                self.assertIn("pas encore disponible", headline)
                self.assertTrue(detail.endswith("."))
                self.assertIn(str(section.delivered_in), detail)

    def test_wording_follows_the_phase_in_progress(self):
        for section in SECTIONS:
            _, detail = placeholder_message(section)
            if section.delivered_in <= IN_PROGRESS_PHASE:
                self.assertIn("prochaine étape", detail)
            else:
                self.assertIn("prévue", detail)

    def test_no_message_pretends_a_feature_exists(self):
        forbidden = ("cliquez", "lancer", "rechercher un", "télécharger un", "importer", "disponible maintenant")
        for section in SECTIONS:
            text = " ".join(placeholder_message(section)).lower()
            for word in forbidden:
                self.assertNotIn(word, text, section.id)


class QtPaletteMappingTests(unittest.TestCase):
    def test_every_role_maps_to_an_existing_hex_token(self):
        for role, token in {**ROLE_TOKENS, **DISABLED_ROLE_TOKENS}.items():
            with self.subTest(role=role):
                self.assertRegex(getattr(DEFAULT_PALETTE, token), r"^#[0-9A-Fa-f]{6}$")

    def test_disabled_roles_are_a_subset_of_the_roles(self):
        self.assertLessEqual(set(DISABLED_ROLE_TOKENS), set(ROLE_TOKENS))

    def test_palette_is_dark_by_the_criterion_qt_uses_for_the_windows_title_bar(self):
        window, text = getattr(DEFAULT_PALETTE, ROLE_TOKENS["Window"]), getattr(DEFAULT_PALETTE, ROLE_TOKENS["WindowText"])
        self.assertGreater(relative_luminance(text), relative_luminance(window))  # texte clair sur fond sombre
        self.assertLess(relative_luminance(window), 0.05)
        self.assertGreaterEqual(contrast_ratio(text, window), 7.0)

    def test_custom_palette_tokens_are_honoured(self):
        self.assertEqual(getattr(Palette(bg="#101010"), ROLE_TOKENS["Window"]), "#101010")


if __name__ == "__main__":
    unittest.main()
