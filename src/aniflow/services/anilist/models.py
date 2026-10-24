"""Modèles de données AniList et analyse tolérante des réponses.

Règle du cahier des charges (§2) : une donnée absente est « inconnue » (None), jamais inventée.
Seul l'identifiant est obligatoire.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .errors import AniListResponseError

UNKNOWN_TITLE = "Titre inconnu"
_TITLE_ORDER = {
    "romaji": ("romaji", "english", "native", "user_preferred"),
    "english": ("english", "romaji", "native", "user_preferred"),
    "native": ("native", "romaji", "english", "user_preferred"),
}


def _opt_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _opt_str(value: Any) -> str | None:
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _opt_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(s for s in (_opt_str(item) for item in value) if s)


@dataclass(frozen=True)
class FuzzyDate:
    year: int | None = None
    month: int | None = None
    day: int | None = None

    @classmethod
    def parse(cls, raw: Any) -> "FuzzyDate":
        if not isinstance(raw, Mapping):
            return cls()
        return cls(_opt_int(raw.get("year")), _opt_int(raw.get("month")), _opt_int(raw.get("day")))

    def iso(self) -> str | None:
        """« 2013-04-07 », « 2013-04 », « 2013 » ou None si la date est inconnue."""
        if self.year is None:
            return None
        if self.month is None:
            return f"{self.year:04d}"
        if self.day is None:
            return f"{self.year:04d}-{self.month:02d}"
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


@dataclass(frozen=True)
class MediaTitle:
    romaji: str | None = None
    english: str | None = None
    native: str | None = None
    user_preferred: str | None = None

    @classmethod
    def parse(cls, raw: Any) -> "MediaTitle":
        if not isinstance(raw, Mapping):
            return cls()
        return cls(
            _opt_str(raw.get("romaji")),
            _opt_str(raw.get("english")),
            _opt_str(raw.get("native")),
            _opt_str(raw.get("userPreferred")),
        )

    def display(self, prefer: str = "romaji") -> str:
        for field_name in _TITLE_ORDER.get(prefer, _TITLE_ORDER["romaji"]):
            value = getattr(self, field_name)
            if value:
                return value
        return UNKNOWN_TITLE


@dataclass(frozen=True)
class MediaSummary:
    id: int
    id_mal: int | None
    media_type: str | None  # ANIME, MANGA…
    title: MediaTitle
    synonyms: tuple[str, ...]
    format: str | None  # TV, TV_SHORT, MOVIE, SPECIAL, OVA, ONA, MUSIC, MANGA, NOVEL, ONE_SHOT
    status: str | None
    episodes: int | None
    duration_min: int | None
    season: str | None
    season_year: int | None
    start_date: FuzzyDate
    end_date: FuzzyDate
    cover_url: str | None
    cover_color: str | None
    genres: tuple[str, ...]
    is_adult: bool | None
    site_url: str | None


@dataclass(frozen=True)
class MediaTag:
    name: str
    rank: int | None
    is_spoiler: bool | None


@dataclass(frozen=True)
class MediaRelation:
    relation_type: str | None  # SEQUEL, PREQUEL, SUMMARY, SIDE_STORY, SOURCE…
    node: MediaSummary


@dataclass(frozen=True)
class MediaDetails:
    summary: MediaSummary
    description: str | None
    average_score: int | None
    tags: tuple[MediaTag, ...]
    relations: tuple[MediaRelation, ...]
    skipped_relations: int  # arêtes illisibles : signalées, jamais ignorées en silence

    @property
    def id(self) -> int:
        return self.summary.id

    @property
    def title(self) -> MediaTitle:
        return self.summary.title


@dataclass(frozen=True)
class SearchPage:
    items: tuple[MediaSummary, ...]
    total: int | None
    current_page: int
    per_page: int | None
    has_next_page: bool

    @classmethod
    def empty(cls) -> "SearchPage":
        return cls((), 0, 1, None, False)


def parse_media_summary(raw: Any) -> MediaSummary:
    if not isinstance(raw, Mapping):
        raise AniListResponseError("entrée média invalide (objet attendu)")
    media_id = _opt_int(raw.get("id"))
    if media_id is None or media_id <= 0:
        raise AniListResponseError("entrée média sans identifiant valide")
    cover = raw.get("coverImage") if isinstance(raw.get("coverImage"), Mapping) else {}
    cover_url = _opt_str(cover.get("extraLarge")) or _opt_str(cover.get("large")) or _opt_str(cover.get("medium"))
    return MediaSummary(
        id=media_id,
        id_mal=_opt_int(raw.get("idMal")),
        media_type=_opt_str(raw.get("type")),
        title=MediaTitle.parse(raw.get("title")),
        synonyms=_str_tuple(raw.get("synonyms")),
        format=_opt_str(raw.get("format")),
        status=_opt_str(raw.get("status")),
        episodes=_opt_int(raw.get("episodes")),
        duration_min=_opt_int(raw.get("duration")),
        season=_opt_str(raw.get("season")),
        season_year=_opt_int(raw.get("seasonYear")),
        start_date=FuzzyDate.parse(raw.get("startDate")),
        end_date=FuzzyDate.parse(raw.get("endDate")),
        cover_url=cover_url,
        cover_color=_opt_str(cover.get("color")),
        genres=_str_tuple(raw.get("genres")),
        is_adult=_opt_bool(raw.get("isAdult")),
        site_url=_opt_str(raw.get("siteUrl")),
    )


def parse_media_details(raw: Any) -> MediaDetails:
    summary = parse_media_summary(raw)
    tags = []
    for tag in raw.get("tags") or []:
        name = _opt_str(tag.get("name")) if isinstance(tag, Mapping) else None
        if name:
            tags.append(MediaTag(name, _opt_int(tag.get("rank")), _opt_bool(tag.get("isMediaSpoiler"))))
    relations: list[MediaRelation] = []
    skipped = 0
    relations_raw = raw.get("relations") if isinstance(raw.get("relations"), Mapping) else {}
    for edge in relations_raw.get("edges") or []:
        try:
            if not isinstance(edge, Mapping):
                raise AniListResponseError("arête invalide")
            relations.append(MediaRelation(_opt_str(edge.get("relationType")), parse_media_summary(edge.get("node"))))
        except AniListResponseError:
            skipped += 1
    return MediaDetails(
        summary=summary,
        description=_opt_str(raw.get("description")),
        average_score=_opt_int(raw.get("averageScore")),
        tags=tuple(tags),
        relations=tuple(relations),
        skipped_relations=skipped,
    )


def parse_search_page(data: Any) -> SearchPage:
    page = data.get("Page") if isinstance(data, Mapping) else None
    if not isinstance(page, Mapping):
        raise AniListResponseError("réponse de recherche sans objet Page")
    info = page.get("pageInfo") if isinstance(page.get("pageInfo"), Mapping) else {}
    items = tuple(parse_media_summary(item) for item in page.get("media") or [])
    return SearchPage(
        items=items,
        total=_opt_int(info.get("total")),
        current_page=_opt_int(info.get("currentPage")) or 1,
        per_page=_opt_int(info.get("perPage")),
        has_next_page=bool(info.get("hasNextPage")),
    )
