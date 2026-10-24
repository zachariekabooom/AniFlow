"""Jetons de design AniFlow : bleu marine très foncé, texte blanc cassé, accent bleu électrique.

Les valeurs de fond respectent le cahier des charges (§11 : proches de #080D1A / #0B1020). Les
contrastes sont vérifiés par les tests (WCAG 2.x) plutôt que supposés.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg_deep: str = "#080D1A"      # barre latérale, zones les plus profondes
    bg: str = "#0B1020"           # fond principal
    surface: str = "#111A32"      # cartes, champs
    surface_raised: str = "#18233F"  # survol, boutons secondaires
    border: str = "#26335A"
    border_strong: str = "#50639E"
    text: str = "#E8ECF6"         # blanc cassé
    text_muted: str = "#9AA6C2"
    text_disabled: str = "#5F6C8C"
    accent: str = "#2D63F5"       # bleu électrique (fonds de boutons, éléments d'interface)
    accent_hover: str = "#3568F7"
    accent_soft: str = "#6C9BFF"  # texte, icônes et anneau de focus sur fond sombre
    accent_dim: str = "#1B2C5A"   # fond de sélection
    on_accent: str = "#FFFFFF"
    danger: str = "#FF6B6B"
    success: str = "#4ADE80"
    warning: str = "#FBBF24"


@dataclass(frozen=True)
class Typography:
    family: str = "Segoe UI"  # présente sur tout Windows ; repli automatique ailleurs
    base_px: int = 14
    small_px: int = 12
    title_px: int = 22
    display_px: int = 30


@dataclass(frozen=True)
class Metrics:
    spacing: tuple[int, ...] = (4, 8, 12, 16, 24, 32, 48)
    radius_control: int = 8
    radius_card: int = 12


DEFAULT_PALETTE = Palette()
DEFAULT_TYPOGRAPHY = Typography()
DEFAULT_METRICS = Metrics()


def _channel(value: int) -> float:
    c = value / 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"couleur hexadécimale attendue (#RRGGBB) : {hex_color!r}")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def contrast_ratio(foreground: str, background: str) -> float:
    a, b = relative_luminance(foreground), relative_luminance(background)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)
