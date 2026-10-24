"""Tests AniFlow. Lancement depuis la racine du dépôt :

    python -m unittest discover -s tests -t . -v      (aucune dépendance)
    python -m pytest                                  (si pytest est installé)
"""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import logging

logging.getLogger("aniflow").addHandler(logging.NullHandler())  # pas de bruit « lastResort » pendant les tests
