"""Barre latérale : logo (si le fichier existe et se lit), six entrées de navigation, version."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from aniflow import APP_NAME
from aniflow.ui.navigation import Section

log = logging.getLogger(__name__)

SIDEBAR_WIDTH = 248
LOGO_HEIGHT = 44


class NavButton(QPushButton):
    """Entrée de navigation : Entrée/Retour la déclenche aussi (Espace est déjà géré par Qt)."""

    def keyPressEvent(self, event) -> None:  # noqa: N802 — nom imposé par Qt
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.click()
            event.accept()
            return
        super().keyPressEvent(event)


def load_logo_pixmap(path: Path | None, height: int, device_pixel_ratio: float) -> QPixmap | None:
    """Logo mis à l'échelle (net sur écran haute densité), ou None s'il est absent ou illisible : jamais de remplaçant."""
    if path is None:
        return None
    try:
        if not Path(path).is_file():
            return None
    except OSError:
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        log.warning("Le fichier du logo est illisible : %s", path)
        return None
    ratio = max(1.0, float(device_pixel_ratio))
    scaled = pixmap.scaledToHeight(max(1, round(height * ratio)), Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(ratio)
    return scaled


class Sidebar(QFrame):
    section_requested = Signal(str)  # identifiant de section demandé par l'utilisateur

    def __init__(self, sections: Sequence[Section], *, logo: Path | None = None, version: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_WIDTH)
        self.setAccessibleName("Navigation principale")
        self._sections = tuple(sections)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 16)
        layout.setSpacing(4)

        self.logo_label: QLabel | None = None
        brand_row = QHBoxLayout()
        brand_row.setSpacing(12)
        pixmap = load_logo_pixmap(logo, LOGO_HEIGHT, self.devicePixelRatioF())
        if pixmap is not None:
            self.logo_label = QLabel()
            self.logo_label.setObjectName("brand-logo")
            self.logo_label.setAccessibleName("Logo AniFlow")
            self.logo_label.setPixmap(pixmap)
            brand_row.addWidget(self.logo_label)
        brand = QLabel(APP_NAME)
        brand.setProperty("role", "brand")
        brand_row.addWidget(brand)
        brand_row.addStretch(1)
        layout.addLayout(brand_row)
        layout.addSpacing(24)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self.buttons: dict[str, NavButton] = {}
        for index, section in enumerate(self._sections):
            button = NavButton(section.label)
            button.setObjectName(f"nav-{section.id}")
            button.setProperty("nav", True)
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.setAccessibleName(section.label)
            button.setToolTip(f"{section.label} ({section.shortcut})")
            self._group.addButton(button, index)
            layout.addWidget(button)
            self.buttons[section.id] = button
        layout.addStretch(1)

        footer = QLabel(f"Version {version}" if version else "")
        footer.setProperty("role", "muted")
        layout.addWidget(footer)

        ordered = list(self.buttons.values())
        for first, second in zip(ordered, ordered[1:]):
            QWidget.setTabOrder(first, second)  # ordre de tabulation explicite : celui de la barre
        self._group.idClicked.connect(self._on_id_clicked)

    def _on_id_clicked(self, index: int) -> None:
        self.section_requested.emit(self._sections[index].id)

    def set_current(self, section_id: str) -> None:
        """Coche l'entrée de la section courante (sans émettre de signal : le modèle de navigation fait foi)."""
        self.buttons[section_id].setChecked(True)
