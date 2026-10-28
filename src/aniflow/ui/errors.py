"""Traduction des exceptions en messages utilisateur français (sans Qt).

Règle : l'écran n'affiche JAMAIS un texte technique ni une trace. Les erreurs des services AniFlow portent
déjà un `user_message` français, repris tel quel ; toute autre exception devient un message générique, son
détail technique restant à part (bouton « Copier les détails », journal).
"""

from __future__ import annotations

from dataclasses import dataclass

from aniflow.database.errors import DatabaseError, SettingsError
from aniflow.net.local_only import NotLocalError
from aniflow.services.ai.errors import AIError, AIResponseError, AIUnavailableError
from aniflow.services.anilist.errors import (
    AniListError,
    AniListHttpError,
    AniListNetworkError,
    AniListNotFoundError,
    AniListRateLimitError,
    AniListResponseError,
    AniListTimeoutError,
)
from aniflow.ui.navigation import UnknownSectionError

GENERIC_TITLE = "Erreur inattendue"
GENERIC_MESSAGE = "Une erreur inattendue s'est produite. Le détail a été enregistré dans le journal de l'application."
MAX_DETAILS = 500


@dataclass(frozen=True)
class UserFacingError:
    title: str
    message: str  # français, affichable tel quel
    details: str  # texte technique (classe + message, tronqué) : « Copier les détails » et journal
    retryable: bool  # vrai si « Réessayer » a un sens (réseau, délai, limite de débit, panne temporaire)
    known: bool  # vrai si l'erreur vient d'un service AniFlow (message dédié) ; faux = message générique


def _safe_str(exc: BaseException) -> str:
    try:
        return str(exc)
    except Exception:  # __str__ défaillant : ne jamais échouer en décrivant une erreur
        return "(message illisible)"


def _technical(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {_safe_str(exc)}"
    return text if len(text) <= MAX_DETAILS else text[: MAX_DETAILS - 1] + "…"


def _classify(exc: BaseException) -> tuple[str, bool]:
    """(titre, « Réessayer » pertinent) selon le type d'erreur ; l'ordre va du plus spécifique au plus général."""
    if isinstance(exc, AniListRateLimitError):
        return "Trop de requêtes", True
    if isinstance(exc, AniListTimeoutError):
        return "Délai dépassé", True
    if isinstance(exc, AniListNetworkError):
        return "Connexion impossible", True
    if isinstance(exc, AniListNotFoundError):
        return "Introuvable", False
    if isinstance(exc, AniListResponseError):
        return "Réponse illisible", True
    if isinstance(exc, AniListHttpError):
        return "Erreur AniList", exc.status >= 500
    if isinstance(exc, AniListError):
        return "Erreur AniList", False
    if isinstance(exc, AIUnavailableError):
        return "IA locale indisponible", True
    if isinstance(exc, AIResponseError):
        return "IA locale", True
    if isinstance(exc, (AIError, NotLocalError)):
        return "IA locale", False
    if isinstance(exc, SettingsError):  # avant DatabaseError, dont elle hérite
        return "Réglage invalide", False
    if isinstance(exc, DatabaseError):
        return "Base de données", False
    if isinstance(exc, UnknownSectionError):
        return "Section inconnue", False
    return "Erreur", False


def describe_exception(exc: BaseException) -> UserFacingError:
    technical = _technical(exc)
    try:
        user_message = getattr(exc, "user_message", None)
    except Exception:  # propriété défaillante
        user_message = None
    if isinstance(user_message, str) and user_message.strip():
        title, retryable = _classify(exc)
        return UserFacingError(title, user_message, technical, retryable, True)
    return UserFacingError(GENERIC_TITLE, GENERIC_MESSAGE, technical, False, False)
