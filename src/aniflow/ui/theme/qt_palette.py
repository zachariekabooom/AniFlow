"""Palette Qt dérivée des jetons de design.

Elle couvre ce que la feuille de style ne peint pas. Elle sert aussi à la barre de titre : depuis Qt 6.4, une palette
d'application sombre donne automatiquement une barre de titre sombre sous Windows (style Fusion requis, voir
application.py). Les correspondances rôle → jeton sont des données pures, testées sans Qt.
"""

from __future__ import annotations

from .tokens import DEFAULT_PALETTE, Palette

# nom d'un QPalette.ColorRole -> nom d'un jeton de Palette
ROLE_TOKENS: dict[str, str] = {
    "Window": "bg",
    "WindowText": "text",
    "Base": "surface",
    "AlternateBase": "surface_raised",
    "Text": "text",
    "Button": "surface_raised",
    "ButtonText": "text",
    "BrightText": "on_accent",
    "Highlight": "accent",
    "HighlightedText": "on_accent",
    "ToolTipBase": "surface_raised",
    "ToolTipText": "text",
    "PlaceholderText": "text_muted",
    "Link": "accent_soft",
    "LinkVisited": "accent_soft",
    "Light": "border_strong",
    "Midlight": "border",
    "Mid": "border",
    "Dark": "bg_deep",
    "Shadow": "bg_deep",
}
DISABLED_ROLE_TOKENS: dict[str, str] = {"WindowText": "text_disabled", "Text": "text_disabled", "ButtonText": "text_disabled"}


def build_palette(palette: Palette = DEFAULT_PALETTE):
    """QPalette sombre issue des jetons (PySide6 requis)."""
    from PySide6.QtGui import QColor, QPalette

    qt_palette = QPalette()
    for role_name, token in ROLE_TOKENS.items():
        qt_palette.setColor(getattr(QPalette.ColorRole, role_name), QColor(getattr(palette, token)))
    for role_name, token in DISABLED_ROLE_TOKENS.items():
        qt_palette.setColor(QPalette.ColorGroup.Disabled, getattr(QPalette.ColorRole, role_name), QColor(getattr(palette, token)))
    return qt_palette
