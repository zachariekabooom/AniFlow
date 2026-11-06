"""Page d'une section dont le contenu n'existe pas encore : un message honnête, aucune commande."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from aniflow.ui.navigation import Section
from aniflow.ui.pages.messages import placeholder_message


class PlaceholderPage(QWidget):
    def __init__(self, section: Section, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.section = section
        self.setObjectName(f"page-{section.id}")
        self.setAccessibleName(section.label)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        headline_text, detail_text = placeholder_message(section)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 36, 40, 36)
        layout.setSpacing(20)

        title = QLabel(section.label)
        title.setProperty("role", "title")
        layout.addWidget(title)

        card = QFrame()
        card.setProperty("card", True)
        card.setMaximumWidth(640)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 20, 24, 20)
        card_layout.setSpacing(8)
        headline = QLabel(headline_text)
        headline.setProperty("role", "headline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setProperty("role", "muted")
        detail.setWordWrap(True)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        layout.addWidget(card, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addStretch(1)
