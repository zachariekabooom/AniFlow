"""Fenêtre principale : barre latérale, pile de pages, raccourcis Ctrl+1…6, mémorisation de l'état de la fenêtre.

La logique de navigation est celle du modèle `NavigationModel` (testé sans Qt) : la fenêtre ne fait que l'afficher.
Aucune page métier n'existe encore ; les sections non livrées affichent un message honnête et aucune commande.
"""

from __future__ import annotations

import base64
import binascii
import logging
from functools import partial
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from aniflow import APP_NAME, __version__
from aniflow.database import SettingsStore
from aniflow.ui.navigation import NavigationModel, Section
from aniflow.ui.pages.placeholder import PlaceholderPage
from aniflow.ui.sidebar import Sidebar

log = logging.getLogger(__name__)

MIN_WIDTH, MIN_HEIGHT = 960, 600
DEFAULT_WIDTH, DEFAULT_HEIGHT = 1280, 800

# Fabriques de pages par identifiant de section ; toute section absente reçoit la page « pas encore disponible ».
PAGE_FACTORIES: dict[str, Callable[[Section], QWidget]] = {}


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: SettingsStore | None = None,
        *,
        logo: Path | None = None,
        persist: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings = settings
        self._persist = persist and settings is not None  # persist=False : lit les préférences, n'écrit rien
        self.setObjectName("main-window")
        self.setMinimumSize(MIN_WIDTH, MIN_HEIGHT)

        self.navigation = NavigationModel.from_setting(self._read("ui.last_section"))

        central = QWidget()
        central.setObjectName("central")
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.sidebar = Sidebar(self.navigation.sections, logo=logo, version=__version__)
        self.stack = QStackedWidget()
        self.stack.setObjectName("pages")
        self.pages: dict[str, QWidget] = {}
        for section in self.navigation.sections:
            page = PAGE_FACTORIES.get(section.id, PlaceholderPage)(section)
            self.pages[section.id] = page
            self.stack.addWidget(page)
        row.addWidget(self.sidebar)
        row.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        self.shortcuts = self._install_shortcuts()
        self.sidebar.section_requested.connect(self.navigation.go_to)
        self.navigation.subscribe(self._on_section_changed)
        self._show_section(self.navigation.current)
        self._restore_geometry()

    # ----- navigation -----

    def _install_shortcuts(self) -> list[QShortcut]:
        shortcuts = []
        for section in self.navigation.sections:
            shortcut = QShortcut(QKeySequence(section.shortcut), self)
            shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
            shortcut.activated.connect(partial(self.navigation.go_to, section.id))
            shortcuts.append(shortcut)
        return shortcuts

    def _show_section(self, section: Section) -> None:
        self.stack.setCurrentIndex(self.navigation.index)
        self.sidebar.set_current(section.id)
        self.setWindowTitle(f"{APP_NAME} — {section.label}")

    def _on_section_changed(self, old: Section, new: Section) -> None:
        self._show_section(new)
        self._write("ui.last_section", new.id)

    # ----- préférences : jamais bloquantes -----

    def _read(self, key: str) -> Any:
        if self._settings is None:
            return None
        try:
            return self._settings.get(key)
        except Exception:  # noqa: BLE001 — une préférence illisible ne doit jamais empêcher d'ouvrir la fenêtre
            log.warning("Préférence %s illisible : valeur par défaut utilisée", key, exc_info=True)
            return None

    def _write(self, key: str, value: Any) -> None:
        if not self._persist:
            return
        try:
            self._settings.set(key, value)
        except Exception:  # noqa: BLE001 — ne jamais empêcher la navigation ni la fermeture
            log.warning("Préférence %s non enregistrée", key, exc_info=True)

    def _restore_geometry(self) -> None:
        self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        stored = self._read("ui.window_geometry")
        if stored is None:
            return
        try:
            raw = base64.b64decode(stored, validate=True)
        except (binascii.Error, ValueError, TypeError):
            log.warning("Position de fenêtre enregistrée illisible : ignorée")
            return
        if not self.restoreGeometry(QByteArray(raw)):
            log.warning("Position de fenêtre enregistrée invalide : ignorée")
            self.resize(DEFAULT_WIDTH, DEFAULT_HEIGHT)

    def _save_geometry(self) -> None:
        raw = bytes(self.saveGeometry().data())
        self._write("ui.window_geometry", base64.b64encode(raw).decode("ascii"))

    def closeEvent(self, event) -> None:  # noqa: N802 — nom imposé par Qt
        self._save_geometry()
        super().closeEvent(event)
