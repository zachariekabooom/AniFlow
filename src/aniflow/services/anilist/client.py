"""Client AniList GraphQL : recherche, fiches et relations.

Limites vérifiées (docs.anilist.co/guide/rate-limiting) : 90 requêtes/min en nominal, mais l'API
est actuellement « dégradée » à 30 requêtes/min, avec un limiteur de rafale en plus. Le client
applique donc 30/min par défaut, un espacement minimal entre appels, une pénalité partagée après
un 429 et un cache TTL. À appeler depuis un thread de travail, jamais depuis le thread de l'UI.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

from aniflow import __version__
from aniflow.net.cache import ResponseCache
from aniflow.net.transport import HttpResponse, HttpTransport, TransportError, UrllibTransport

from . import queries
from .errors import (
    AniListGraphQLError,
    AniListHttpError,
    AniListNetworkError,
    AniListNotFoundError,
    AniListRateLimitError,
    AniListResponseError,
    AniListTimeoutError,
)
from .models import MediaDetails, SearchPage, parse_media_details, parse_search_page
from .ratelimit import RateLimitWouldBlock, SlidingWindowRateLimiter

ENDPOINT = "https://graphql.anilist.co"
DEFAULT_MAX_CALLS_PER_MINUTE = 30
MAX_BATCH = 50
log = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitInfo:
    limit: int | None
    remaining: int | None


def _int_header(response: HttpResponse, name: str) -> int | None:
    try:
        return int(float(response.header(name) or ""))
    except ValueError:
        return None


def _retry_after_seconds(response: HttpResponse) -> float:
    value = response.header("retry-after")
    try:
        seconds = float(value) if value is not None else 60.0
    except ValueError:
        seconds = 60.0
    return min(max(seconds, 1.0), 3600.0)


def _error_messages(payload: Any) -> list[str]:
    errors = payload.get("errors") if isinstance(payload, Mapping) else None
    if not isinstance(errors, list):
        return []
    return [str(e.get("message", e)) if isinstance(e, Mapping) else str(e) for e in errors]


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} doit être un entier positif")
    return value


class AniListClient:
    def __init__(
        self,
        transport: HttpTransport | None = None,
        *,
        endpoint: str = ENDPOINT,
        limiter: SlidingWindowRateLimiter | None = None,
        cache: ResponseCache | None = None,
        timeout: float = 15.0,
        max_retries: int = 2,
        max_wait: float = 15.0,
        search_ttl: float = 6 * 3600.0,
        details_ttl: float = 7 * 86400.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport or UrllibTransport()
        self._endpoint = endpoint
        self._limiter = limiter or SlidingWindowRateLimiter(DEFAULT_MAX_CALLS_PER_MINUTE, 60.0, 0.5)
        self._cache = cache
        self._timeout = timeout
        self._max_retries = max_retries
        self._max_wait = max_wait
        self._search_ttl = search_ttl
        self._details_ttl = details_ttl
        self._sleep = sleep
        self.last_rate_limit: RateLimitInfo | None = None  # information de diagnostic (non synchronisée)

    # ----- API publique -----

    def search_anime(self, text: str, *, page: int = 1, per_page: int = 10, include_adult: bool = False) -> SearchPage:
        text = (text or "").strip()
        if not text:
            return SearchPage.empty()
        variables: dict[str, Any] = {"search": text, "page": max(1, int(page)), "perPage": max(1, min(int(per_page), MAX_BATCH))}
        if not include_adult:
            variables["isAdult"] = False
        data = self._execute(queries.search_anime(include_adult), variables, ttl=self._search_ttl)
        return parse_search_page(data)

    def get_anime(self, media_id: int) -> MediaDetails:
        media_id = _positive_int(media_id, "media_id")
        data = self._execute(queries.ANIME_DETAILS, {"id": media_id}, ttl=self._details_ttl)
        media = data.get("Media")
        if not media:
            raise AniListNotFoundError("fiche absente de la réponse")
        return parse_media_details(media)

    def get_anime_batch(self, media_ids: Sequence[int]) -> dict[int, MediaDetails]:
        """Fiches complètes (relations incluses) par lots de 50. Les identifiants inconnus sont absents."""
        unique = list(dict.fromkeys(_positive_int(i, "media_id") for i in media_ids))
        results: dict[int, MediaDetails] = {}
        for start in range(0, len(unique), MAX_BATCH):
            chunk = unique[start : start + MAX_BATCH]
            data = self._execute(queries.ANIME_DETAILS_BATCH, {"ids": chunk, "perPage": len(chunk)}, ttl=self._details_ttl)
            page = data.get("Page")
            if not isinstance(page, Mapping):
                raise AniListResponseError("réponse de lot sans objet Page")
            for media in page.get("media") or []:
                details = parse_media_details(media)
                results[details.id] = details
        return results

    # ----- Exécution -----

    def _execute(self, query: str, variables: Mapping[str, Any], *, ttl: float) -> dict[str, Any]:
        key = self._cache_key(query, variables)
        if self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        body = json.dumps({"query": query, "variables": dict(variables)}, separators=(",", ":")).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"AniFlow/{__version__} (application de bureau personnelle)",
        }
        attempt = 0
        while True:
            attempt += 1
            try:
                self._limiter.acquire(max_wait=self._max_wait)
            except RateLimitWouldBlock as exc:
                raise AniListRateLimitError(exc.wait) from exc
            try:
                response = self._transport.request("POST", self._endpoint, body=body, headers=headers, timeout=self._timeout)
            except TransportError as exc:
                if exc.is_timeout:
                    raise AniListTimeoutError(str(exc)) from exc
                raise AniListNetworkError(str(exc)) from exc

            self.last_rate_limit = RateLimitInfo(_int_header(response, "x-ratelimit-limit"), _int_header(response, "x-ratelimit-remaining"))
            status = response.status
            if status == 429:
                wait = _retry_after_seconds(response)
                self._limiter.penalize(wait)
                if attempt <= self._max_retries and wait <= self._max_wait:
                    log.warning("AniList 429 : nouvelle tentative après %.0f s", wait)
                    continue
                raise AniListRateLimitError(wait)
            if 500 <= status < 600:
                if attempt <= self._max_retries:
                    self._sleep(min(2 ** (attempt - 1), 8))
                    continue
                raise AniListHttpError(status, _error_messages(self._json_or_none(response)))

            data = self._decode(response)
            if self._cache is not None:
                self._cache.set(key, data, ttl)
            return data

    @staticmethod
    def _json_or_none(response: HttpResponse) -> Any:
        if not response.body:
            return None
        try:
            return json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    def _decode(self, response: HttpResponse) -> dict[str, Any]:
        status = response.status
        payload = self._json_or_none(response)
        messages = _error_messages(payload)
        if status == 404:
            raise AniListNotFoundError(messages)
        if 300 <= status < 400:
            raise AniListHttpError(status, "redirection inattendue")
        if status == 400:
            raise AniListGraphQLError(messages or ["requête invalide"])
        if not 200 <= status < 300:
            raise AniListHttpError(status, messages)
        if not isinstance(payload, dict):
            raise AniListResponseError("réponse JSON invalide")
        data = payload.get("data")
        if messages and not data:
            raise AniListGraphQLError(messages)
        if not isinstance(data, dict):
            raise AniListResponseError("réponse sans champ data")
        return data

    def _cache_key(self, query: str, variables: Mapping[str, Any]) -> str:
        raw = json.dumps([self._endpoint, query, dict(variables)], sort_keys=True, separators=(",", ":"))
        return "anilist:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
