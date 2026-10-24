"""Fournisseur de métadonnées AniList (GraphQL)."""

from .client import AniListClient
from .errors import (
    AniListError,
    AniListGraphQLError,
    AniListHttpError,
    AniListNetworkError,
    AniListNotFoundError,
    AniListRateLimitError,
    AniListResponseError,
    AniListTimeoutError,
)
from .models import MediaDetails, MediaRelation, MediaSummary, SearchPage

__all__ = [
    "AniListClient",
    "AniListError",
    "AniListGraphQLError",
    "AniListHttpError",
    "AniListNetworkError",
    "AniListNotFoundError",
    "AniListRateLimitError",
    "AniListResponseError",
    "AniListTimeoutError",
    "MediaDetails",
    "MediaRelation",
    "MediaSummary",
    "SearchPage",
]
