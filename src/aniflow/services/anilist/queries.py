"""Requêtes GraphQL AniList. Champs et énumérations vérifiés sur docs.anilist.co (oct. 2026)."""

from __future__ import annotations

CORE_FIELDS = """
  id idMal type format status episodes duration season seasonYear
  title { romaji english native userPreferred }
  synonyms genres isAdult siteUrl
  startDate { year month day }
  endDate { year month day }
  coverImage { extraLarge large medium color }
"""

# relationType(version: 2) expose aussi SOURCE, COMPILATION et CONTAINS ; SUMMARY désigne un récapitulatif.
DETAIL_FIELDS = (
    CORE_FIELDS
    + """
  description(asHtml: false)
  averageScore
  tags { name rank isMediaSpoiler }
  relations {
    edges {
      relationType(version: 2)
      node {"""
    + CORE_FIELDS
    + """}
    }
  }
"""
)

PAGE_INFO = "pageInfo { total perPage currentPage lastPage hasNextPage }"


def search_anime(include_adult: bool) -> str:
    """Recherche paginée. Sans $isAdult, AniList ne filtre pas le contenu adulte."""
    if include_adult:
        header = "query ($search: String!, $page: Int, $perPage: Int)"
        args = "search: $search, type: ANIME, sort: SEARCH_MATCH"
    else:
        header = "query ($search: String!, $page: Int, $perPage: Int, $isAdult: Boolean)"
        args = "search: $search, type: ANIME, sort: SEARCH_MATCH, isAdult: $isAdult"
    return (
        f"{header} {{ Page(page: $page, perPage: $perPage) {{ {PAGE_INFO} "
        f"media({args}) {{{CORE_FIELDS}}} }} }}"
    )


ANIME_DETAILS = "query ($id: Int!) { Media(id: $id, type: ANIME) {" + DETAIL_FIELDS + "} }"

# Lot : jusqu'à 50 fiches par requête (indispensable sous la limite actuelle de 30 requêtes/min).
ANIME_DETAILS_BATCH = (
    "query ($ids: [Int], $perPage: Int) { Page(page: 1, perPage: $perPage) { "
    "media(id_in: $ids, type: ANIME) {" + DETAIL_FIELDS + "} } }"
)
