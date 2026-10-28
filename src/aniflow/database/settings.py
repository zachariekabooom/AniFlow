"""Paramètres persistants (clé/valeur JSON) avec registre de clés connues et validation.

La validation applique la politique « IA locale exclusive » dès la configuration : une adresse
ou un modèle cloud ne peut même pas être enregistré.
"""

from __future__ import annotations

import base64
import binascii
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from aniflow.net.local_only import (
    DEFAULT_OLLAMA_URL,
    NotLocalError,
    ensure_not_cloud_name,
    validate_local_base_url,
)

from aniflow.ui.navigation import DEFAULT_SECTION_ID, SECTION_IDS

from .errors import SettingsError


@dataclass(frozen=True)
class SettingSpec:
    default: Any
    validate: Callable[[Any], Any] | None = None


def _ollama_url(value: Any) -> str:
    try:
        return validate_local_base_url(value)
    except NotLocalError as exc:
        raise SettingsError(str(exc), user_message=exc.user_message) from exc


def _model_name(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SettingsError("nom de modèle invalide", user_message="Le nom du modèle IA doit être un texte non vide.")
    try:
        ensure_not_cloud_name(value.strip())
    except NotLocalError as exc:
        raise SettingsError(str(exc), user_message=exc.user_message) from exc
    return value.strip()


def _bool(value: Any) -> bool:
    if not isinstance(value, bool):
        raise SettingsError("booléen attendu", user_message="Valeur invalide : oui/non attendu.")
    return value


def _choice(*allowed: str) -> Callable[[Any], str]:
    def check(value: Any) -> str:
        if value not in allowed:
            raise SettingsError(f"valeur hors liste : {value!r}", user_message=f"Valeur invalide ; choix possibles : {', '.join(allowed)}.")
        return value

    return check


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SettingsError("texte attendu", user_message="Valeur invalide : texte non vide attendu.")
    return value.strip()


MAX_GEOMETRY_BYTES = 4096  # QWidget.saveGeometry() produit une centaine d'octets ; large marge, jamais de contenu libre


def _section_id(value: Any) -> str:
    if not isinstance(value, str) or value not in SECTION_IDS:
        raise SettingsError(
            f"section inconnue : {value!r}",
            user_message="Cette section de l'application n'existe pas.",
        )
    return value


def _window_geometry(value: Any) -> str | None:
    """Géométrie de fenêtre enregistrée en base64 (octets opaques de Qt) ; None = aucune."""
    if value is None:
        return None
    invalid = SettingsError("géométrie invalide", user_message="La position enregistrée de la fenêtre est invalide.")
    if not isinstance(value, str) or not value:
        raise invalid
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError):
        raise invalid from None
    if not 0 < len(raw) <= MAX_GEOMETRY_BYTES:
        raise invalid
    return value


SETTINGS: dict[str, SettingSpec] = {
    "ai.ollama_url": SettingSpec(DEFAULT_OLLAMA_URL, _ollama_url),
    "ai.model": SettingSpec(None, _model_name),
    "anilist.include_adult": SettingSpec(False, _bool),
    "ui.title_language": SettingSpec("romaji", _choice("romaji", "english", "native")),
    "ui.last_section": SettingSpec(DEFAULT_SECTION_ID, _section_id),
    "ui.window_geometry": SettingSpec(None, _window_geometry),
    "downloads.dir": SettingSpec(None, _optional_text),
}


class SettingsStore:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    @staticmethod
    def _spec(key: str) -> SettingSpec:
        try:
            return SETTINGS[key]
        except KeyError:
            raise SettingsError(f"paramètre inconnu : {key}", user_message=f"Paramètre inconnu : {key}.") from None

    def get(self, key: str) -> Any:
        spec = self._spec(key)
        row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return spec.default if row is None else json.loads(row["value"])

    def set(self, key: str, value: Any) -> Any:
        spec = self._spec(key)
        checked = spec.validate(value) if spec.validate else value
        self._conn.execute(
            "INSERT INTO settings(key, value, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, json.dumps(checked, ensure_ascii=False), datetime.now(timezone.utc).isoformat(timespec="seconds")),
        )
        return checked

    def reset(self, key: str) -> None:
        self._spec(key)
        self._conn.execute("DELETE FROM settings WHERE key = ?", (key,))

    def all(self) -> dict[str, Any]:
        return {key: self.get(key) for key in SETTINGS}
