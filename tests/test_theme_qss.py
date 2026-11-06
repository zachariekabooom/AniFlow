import re
import unittest

from aniflow.ui.theme import DEFAULT_PALETTE as P
from aniflow.ui.theme import build_stylesheet, contrast_ratio

# Propriétés de feuille de style Qt (documentation « Qt Style Sheets Reference ») utilisées par AniFlow.
ALLOWED_PROPERTIES = {
    "background", "background-color", "border", "border-radius", "border-color", "border-left", "border-right",
    "color", "font-family", "font-size", "font-weight", "height", "margin", "min-height", "min-width", "outline",
    "padding", "selection-background-color", "selection-color", "text-align", "width",
}
ALLOWED_PSEUDO_STATES = {"hover", "pressed", "focus", "disabled", "checked", "selected", "enabled", "vertical", "horizontal"}
ALLOWED_SUBCONTROLS = {"item", "handle", "add-line", "sub-line"}
RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def rules(qss):
    return [(selector.strip(), body) for selector, body in RULE.findall(qss)]


def lint_problems(qss):
    """Problèmes de syntaxe d'une feuille de style (Qt ne les signale que par un avertissement, sans échec)."""
    problems = []
    if RULE.sub("", qss).strip():
        problems.append("texte hors d'une règle bien formée")
    if qss.count("{") != qss.count("}"):
        problems.append("accolades déséquilibrées")
    for selector, body in rules(qss):
        if not re.search(r";\s*$", body):
            problems.append(f"{selector} : déclaration non terminée par « ; »")
        for declaration in [d for d in body.split(";") if d.strip()]:
            name, _, value = declaration.partition(":")
            if name.strip() not in ALLOWED_PROPERTIES:
                problems.append(f"{selector} : propriété inconnue {name.strip()!r}")
            if not value.strip():
                problems.append(f"{selector} : valeur vide pour {name.strip()!r}")
            if ":" in value:  # aucune valeur de notre feuille de style ne contient « : » : c'est une déclaration collée à la suivante
                problems.append(f"{selector} : « ; » manquant après {name.strip()!r}")
        for part in selector.split(","):
            bare = re.sub(r"\[[^\]]*\]", "", part)
            problems += [f"{part.strip()} : sous-contrôle inconnu {c!r}" for c in re.findall(r"::([\w-]+)", bare) if c not in ALLOWED_SUBCONTROLS]
            problems += [f"{part.strip()} : état inconnu {st!r}" for st in re.findall(r"(?<!:):([\w-]+)", bare) if st not in ALLOWED_PSEUDO_STATES]
    return problems


class StylesheetLintTests(unittest.TestCase):
    def setUp(self):
        self.qss = build_stylesheet()

    def test_the_generated_stylesheet_has_no_lint_problem(self):
        self.assertEqual(lint_problems(self.qss), [])

    def test_the_lint_detects_the_typical_mistakes(self):
        mutations = {
            "propriété mal écrite": self.qss.replace("text-align: left;", "text-allign: left;", 1),
            "point-virgule manquant": self.qss.replace("text-align: left;", "text-align: left", 1),
            "état inconnu": self.qss.replace(":checked", ":chekced", 1),
            "sous-contrôle inconnu": self.qss.replace("::handle", "::handel", 1),
            "accolade en trop": self.qss + "}",
            "texte parasite": self.qss + "\ncolor: red;\n",
            "valeur vide": self.qss.replace("text-align: left;", "text-align: ;", 1),
        }
        for name, mutated in mutations.items():
            with self.subTest(name):
                self.assertNotEqual(mutated, self.qss, "la mutation ne change rien : motif introuvable")
                self.assertTrue(lint_problems(mutated), f"« {name} » n'a pas été détectée")

    def test_sidebar_and_navigation_rules_exist(self):
        selectors = {s for s, _ in rules(self.qss)}
        for expected in ("QFrame#sidebar", 'QPushButton[nav="true"]', 'QPushButton[nav="true"]:hover', 'QPushButton[nav="true"]:checked', 'QPushButton[nav="true"]:focus'):
            self.assertIn(expected, selectors)

    def test_navigation_states_use_the_resolved_tokens(self):
        for token in (P.bg_deep, P.accent_dim, P.accent_soft, P.surface_raised, P.text_muted):
            self.assertIn(token, self.qss)


class NavigationContrastTests(unittest.TestCase):
    def test_text_in_each_navigation_state_is_readable(self):
        pairs = {
            "entrée au repos": (P.text_muted, P.bg_deep),
            "entrée survolée": (P.text, P.surface_raised),
            "entrée active": (P.text, P.accent_dim),
            "titre de la page": (P.text, P.bg),
            "texte secondaire d'une carte": (P.text_muted, P.surface),
        }
        for name, (fg, bg) in pairs.items():
            with self.subTest(name):
                self.assertGreaterEqual(contrast_ratio(fg, bg), 4.5, name)

    def test_focus_ring_and_active_marker_stand_out(self):
        self.assertGreaterEqual(contrast_ratio(P.accent_soft, P.bg_deep), 3.0)  # anneau de focus sur la barre latérale
        self.assertGreaterEqual(contrast_ratio(P.accent_soft, P.accent_dim), 3.0)  # repère de l'entrée active


if __name__ == "__main__":
    unittest.main()
