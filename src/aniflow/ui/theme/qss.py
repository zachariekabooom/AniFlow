"""Génération de la feuille de style Qt (QSS) à partir des jetons de design."""

from __future__ import annotations

from dataclasses import asdict
from string import Template

from .tokens import DEFAULT_METRICS, DEFAULT_PALETTE, DEFAULT_TYPOGRAPHY, Metrics, Palette, Typography

_TEMPLATE = Template(
    """
QWidget {
    background-color: $bg;
    color: $text;
    font-family: "$family";
    font-size: ${base_px}px;
}
QMainWindow, QDialog { background-color: $bg; }
QLabel { background: transparent; }
QLabel[role="title"] { font-size: ${title_px}px; font-weight: 600; }
QLabel[role="muted"] { color: $text_muted; font-size: ${small_px}px; }
QLabel[role="error"] { color: $danger; }
QFrame[card="true"] {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: ${radius_card}px;
}
QPushButton {
    background-color: $surface_raised;
    border: 1px solid $border;
    border-radius: ${radius_control}px;
    padding: 8px 16px;
}
QPushButton:hover { border-color: $accent_soft; }
QPushButton:pressed { background-color: $surface; }
QPushButton:focus { border: 2px solid $accent_soft; padding: 7px 15px; }
QPushButton:disabled { color: $text_disabled; background-color: $surface; border-color: $border; }
QPushButton[variant="primary"] {
    background-color: $accent;
    border-color: $accent;
    color: $on_accent;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover { background-color: $accent_hover; border-color: $accent_hover; }
QPushButton[variant="primary"]:focus { border: 2px solid $accent_soft; }
QLineEdit, QComboBox, QSpinBox {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: ${radius_control}px;
    padding: 8px 12px;
    selection-background-color: $accent;
    selection-color: $on_accent;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus { border: 2px solid $accent_soft; padding: 7px 11px; }
QListView, QListWidget, QTreeView, QTableView {
    background-color: $surface;
    border: 1px solid $border;
    border-radius: ${radius_control}px;
    outline: 0;
}
QListView::item:selected, QListWidget::item:selected, QTreeView::item:selected {
    background-color: $accent_dim;
    color: $text;
}
QListView::item:hover, QListWidget::item:hover { background-color: $surface_raised; }
QScrollBar:vertical { width: 10px; background: transparent; margin: 0; }
QScrollBar::handle:vertical { background: $border_strong; border-radius: 5px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { height: 10px; background: transparent; margin: 0; }
QScrollBar::handle:horizontal { background: $border_strong; border-radius: 5px; min-width: 28px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QToolTip {
    background-color: $surface_raised;
    color: $text;
    border: 1px solid $border;
    padding: 4px 8px;
}
"""
)


def build_stylesheet(
    palette: Palette = DEFAULT_PALETTE,
    typography: Typography = DEFAULT_TYPOGRAPHY,
    metrics: Metrics = DEFAULT_METRICS,
) -> str:
    values = {**asdict(palette), **asdict(typography)}
    values["radius_control"] = metrics.radius_control
    values["radius_card"] = metrics.radius_card
    return _TEMPLATE.substitute(values)  # KeyError si un jeton manque : jamais de style à moitié résolu
