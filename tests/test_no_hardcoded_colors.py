import re
import tempfile
import unittest
from pathlib import Path

UI_ROOT = Path(__file__).resolve().parents[1] / "src" / "aniflow" / "ui"
TOKENS = UI_ROOT / "theme" / "tokens.py"
COLOR = re.compile(r"#[0-9A-Fa-f]{3,8}\b|\b(?:rgba?|hsla?)\s*\(")


def find_hardcoded_colors(root, exempt=()):
    """Couleurs codées en dur (#RGB, #RRGGBB…, rgb(), hsl()) dans les sources Python, hors fichiers exemptés."""
    found = []
    for path in sorted(Path(root).rglob("*.py")):
        if path in exempt:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if COLOR.search(line):
                found.append(f"{path.relative_to(root).as_posix()}:{number}")
    return found


class HardcodedColorTests(unittest.TestCase):
    def test_ui_sources_take_every_color_from_the_theme_tokens(self):
        self.assertTrue(TOKENS.is_file())
        self.assertEqual(find_hardcoded_colors(UI_ROOT, exempt={TOKENS}), [], "couleur codée en dur : utiliser un jeton de ui/theme/tokens.py")

    def test_detector_flags_hex_and_functional_notations(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "mauvais.py").write_text('A = "#FF00FF"\nB = "#abc"\nC = "rgba(0, 0, 0, 0.5)"\nD = "hsl(10 20% 30%)"\n', encoding="utf-8")
            (root / "bon.py").write_text('A = f"#{n}"\nB = "#12"\nC = "transparent"\nD = "ordre #1"\n', encoding="utf-8")
            (root / "tokens.py").write_text('A = "#FF00FF"\n', encoding="utf-8")
            self.assertEqual(find_hardcoded_colors(root, exempt={root / "tokens.py"}), ["mauvais.py:1", "mauvais.py:2", "mauvais.py:3", "mauvais.py:4"])


if __name__ == "__main__":
    unittest.main()
