"""Réponses AniList synthétiques, conformes au schéma documenté (docs.anilist.co), sans données réelles."""

from __future__ import annotations

from typing import Any


def media_node(media_id: int, *, title: str = "Série de test", fmt: str | None = "TV", episodes: int | None = 12, **extra: Any) -> dict[str, Any]:
    node: dict[str, Any] = {
        "id": media_id,
        "idMal": media_id + 10000,
        "type": "ANIME",
        "format": fmt,
        "status": "FINISHED",
        "episodes": episodes,
        "duration": 24,
        "season": "FALL",
        "seasonYear": 2023,
        "title": {"romaji": title, "english": f"{title} (EN)", "native": f"{title} (JP)", "userPreferred": title},
        "synonyms": ["Alias A", "  ", "Alias B"],
        "genres": ["Adventure", "Fantasy"],
        "isAdult": False,
        "siteUrl": f"https://anilist.co/anime/{media_id}",
        "startDate": {"year": 2023, "month": 9, "day": 29},
        "endDate": {"year": 2024, "month": 3, "day": None},
        "coverImage": {"extraLarge": f"https://img.example/{media_id}-xl.jpg", "large": None, "medium": None, "color": "#e4a15d"},
    }
    node.update(extra)
    return node


def search_response(ids: list[int], *, has_next: bool = False, total: int | None = None) -> dict[str, Any]:
    return {
        "data": {
            "Page": {
                "pageInfo": {"total": total if total is not None else len(ids), "perPage": 10, "currentPage": 1, "lastPage": 1, "hasNextPage": has_next},
                "media": [media_node(i, title=f"Résultat {i}") for i in ids],
            }
        }
    }


def details_node(media_id: int = 1001) -> dict[str, Any]:
    node = media_node(media_id, title="Série principale")
    node.update(
        description="Synopsis de test.\nSeconde ligne.",
        averageScore=84,
        tags=[{"name": "Elf", "rank": 90, "isMediaSpoiler": False}, {"name": "", "rank": 1, "isMediaSpoiler": False}, "invalide"],
        relations={
            "edges": [
                {"relationType": "SEQUEL", "node": media_node(1002, title="Saison 2")},
                {"relationType": "SOURCE", "node": media_node(5001, title="Manga source", fmt="MANGA", episodes=None, type="MANGA")},
                {"relationType": "SUMMARY", "node": media_node(1003, title="Récapitulatif", fmt="SPECIAL", episodes=1)},
                {"relationType": "OTHER", "node": None},  # arête illisible : doit être comptée, pas ignorée en silence
            ]
        },
    )
    return node


def details_response(media_id: int = 1001) -> dict[str, Any]:
    return {"data": {"Media": details_node(media_id)}}


def batch_response(ids: list[int]) -> dict[str, Any]:
    return {"data": {"Page": {"media": [details_node(i) for i in ids]}}}
