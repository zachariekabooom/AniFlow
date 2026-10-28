"""Modèle de navigation principal, sans dépendance à Qt (testable partout).

L'ordre et les libellés suivent SPEC.md §11 : Accueil / Continuer, Recherche, Ma bibliothèque,
Téléchargements, Statistiques, Paramètres. Les identifiants sont PERSISTÉS dans les paramètres
(`ui.last_section`) : ne jamais les renommer sans migration.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Sequence

_ID_FORMAT = re.compile(r"^[a-z][a-z0-9_]*$")


class UnknownSectionError(ValueError):
    """Identifiant de section inconnu."""

    def __init__(self, section_id: object) -> None:
        super().__init__(f"section inconnue : {section_id!r}")
        self.user_message = "Cette section de l'application n'existe pas."


@dataclass(frozen=True)
class Section:
    id: str  # identifiant stable, persisté
    label: str  # libellé français affiché
    shortcut: str  # syntaxe QKeySequence : « Ctrl+1 »…
    icon: str  # identifiant logique d'icône (fichier associé ajouté à l'étape E4)
    delivered_in: int  # phase de ROADMAP.md qui livre le contenu de la section


SECTIONS: tuple[Section, ...] = (
    Section("accueil", "Accueil / Continuer", "Ctrl+1", "home", 3),
    Section("recherche", "Recherche", "Ctrl+2", "search", 2),
    Section("bibliotheque", "Ma bibliothèque", "Ctrl+3", "library", 3),
    Section("telechargements", "Téléchargements", "Ctrl+4", "download", 5),
    Section("statistiques", "Statistiques", "Ctrl+5", "statistics", 4),
    Section("parametres", "Paramètres", "Ctrl+6", "settings", 1),
)
SECTION_IDS: tuple[str, ...] = tuple(section.id for section in SECTIONS)
DEFAULT_SECTION_ID = SECTIONS[0].id


def validate_sections(sections: Sequence[Section]) -> None:
    """Invariants du catalogue : non vide, identifiants et raccourcis uniques, formats corrects."""
    if not sections:
        raise ValueError("le catalogue de sections est vide")
    ids = [s.id for s in sections]
    shortcuts = [s.shortcut for s in sections]
    if len(set(ids)) != len(ids):
        raise ValueError("identifiants de section en double")
    if len(set(shortcuts)) != len(shortcuts) or not all(shortcuts):
        raise ValueError("raccourcis de section en double ou vides")
    for section in sections:
        if not _ID_FORMAT.match(section.id):
            raise ValueError(f"identifiant de section invalide : {section.id!r}")
        if not section.label.strip() or section.delivered_in < 1:
            raise ValueError(f"section incomplète : {section.id!r}")


def section_by_id(section_id: object) -> Section:
    for section in SECTIONS:
        if section.id == section_id:
            return section
    raise UnknownSectionError(section_id)


class NavigationModel:
    """Section courante + abonnements aux changements (relié à l'interface à l'étape E3)."""

    def __init__(self, current_id: str = DEFAULT_SECTION_ID, sections: Sequence[Section] = SECTIONS) -> None:
        validate_sections(sections)
        self._sections = tuple(sections)
        self._index = self._index_of(current_id)
        self._listeners: list[Callable[[Section, Section], None]] = []

    @classmethod
    def from_setting(cls, stored: object, sections: Sequence[Section] = SECTIONS) -> "NavigationModel":
        """Construit le modèle depuis une valeur enregistrée ; toute valeur inconnue donne la section par défaut."""
        known = [s.id for s in sections]
        return cls(stored if isinstance(stored, str) and stored in known else sections[0].id, sections)

    @property
    def sections(self) -> tuple[Section, ...]:
        return self._sections

    @property
    def current(self) -> Section:
        return self._sections[self._index]

    @property
    def index(self) -> int:
        return self._index

    def go_to(self, section_id: str) -> Section:
        new_index = self._index_of(section_id)
        if new_index != self._index:
            old = self.current
            self._index = new_index
            for listener in list(self._listeners):
                listener(old, self.current)
        return self.current

    def subscribe(self, listener: Callable[[Section, Section], None]) -> Callable[[], None]:
        """Abonne `listener(ancienne, nouvelle)` ; retourne la fonction de désabonnement (idempotente)."""
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def _index_of(self, section_id: object) -> int:
        for index, section in enumerate(self._sections):
            if section.id == section_id:
                return index
        raise UnknownSectionError(section_id)
