"""Aides des tests d'interface : PySide6 est facultatif, ces tests sont alors ignorés (pas en échec)."""

from __future__ import annotations

import importlib.util
import unittest

HAS_QT = importlib.util.find_spec("PySide6") is not None
requires_qt = unittest.skipUnless(HAS_QT, "PySide6 absent : tests d'interface ignorés")
