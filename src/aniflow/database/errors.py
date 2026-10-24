"""Erreurs de la couche de persistance, avec messages français."""

from __future__ import annotations


class DatabaseError(Exception):
    default_user_message = "Erreur de base de données locale."

    def __init__(self, message: str | None = None, *, user_message: str | None = None) -> None:
        super().__init__(message or user_message or self.default_user_message)
        self.user_message = user_message or self.default_user_message


class DatabaseTooNewError(DatabaseError):
    def __init__(self, found: int, supported: int) -> None:
        super().__init__(
            f"schéma v{found} > v{supported}",
            user_message=(
                f"Cette base a été créée par une version plus récente d'AniFlow (schéma v{found}, "
                f"cette version gère jusqu'à v{supported}). Mettez AniFlow à jour ou restaurez une sauvegarde plus ancienne."
            ),
        )


class DatabaseCorruptError(DatabaseError):
    default_user_message = "Le fichier de base de données est illisible ou corrompu. Restaurez une sauvegarde."


class DatabaseRestoreError(DatabaseError):
    default_user_message = "La restauration a échoué ; la base actuelle n'a pas été modifiée. Fermez AniFlow puis réessayez."


class MigrationError(DatabaseError):
    def __init__(self, version: int, detail: str) -> None:
        super().__init__(
            f"migration v{version} échouée : {detail}",
            user_message=f"La mise à jour de la base (étape {version}) a échoué et a été annulée. Une sauvegarde a été conservée.",
        )
        self.version = version


class SettingsError(DatabaseError, ValueError):
    pass
