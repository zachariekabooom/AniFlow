"""Erreurs du client AniList. Chacune porte un message français directement affichable."""

from __future__ import annotations

from typing import Sequence


class AniListError(Exception):
    default_user_message = "AniList a renvoyé une erreur inattendue. Réessayez dans un instant."

    def __init__(self, message: str | None = None, *, user_message: str | None = None) -> None:
        super().__init__(message or user_message or self.default_user_message)
        self.user_message = user_message or self.default_user_message


class AniListNetworkError(AniListError):
    default_user_message = "Impossible de joindre AniList. Vérifiez votre connexion Internet, puis réessayez."


class AniListTimeoutError(AniListNetworkError):
    default_user_message = "AniList met trop de temps à répondre. Réessayez dans un instant."


class AniListHttpError(AniListError):
    def __init__(self, status: int, detail: str | Sequence[str] | None = None, *, user_message: str | None = None) -> None:
        if detail is None or isinstance(detail, str):
            detail_text = detail or ""
        else:
            detail_text = "; ".join(detail)
        message = f"HTTP {status}" + (f" : {detail_text}" if detail_text else "")
        super().__init__(
            message,
            user_message=user_message or f"AniList a répondu avec une erreur (code {status}). Réessayez plus tard.",
        )
        self.status = status
        self.detail = detail_text


class AniListRateLimitError(AniListHttpError):
    def __init__(self, retry_after: float) -> None:
        seconds = max(1, int(round(retry_after)))
        super().__init__(
            429,
            f"limite de débit, attendre {seconds} s",
            user_message=f"Trop de requêtes envoyées à AniList. Réessayez dans {seconds} s.",
        )
        self.retry_after = float(retry_after)


class AniListNotFoundError(AniListHttpError):
    def __init__(self, detail: str | Sequence[str] | None = None) -> None:
        super().__init__(404, detail, user_message="Cette fiche est introuvable sur AniList.")


class AniListGraphQLError(AniListError):
    def __init__(self, messages: Sequence[str]) -> None:
        text = "; ".join(messages) if messages else "requête refusée"
        super().__init__(
            f"GraphQL : {text}",
            user_message="AniList a refusé la requête. Si le problème persiste, consultez le journal de l'application.",
        )
        self.messages = tuple(messages)


class AniListResponseError(AniListError):
    default_user_message = "La réponse d'AniList est illisible. Réessayez dans un instant."
