#!/usr/bin/env python3
"""Sonde phase 0 — AniList GraphQL en conditions réelles : recherche, fiche, relations, lot, 404, cache.

    python tools/phase0/anilist_probe.py --query "Sousou no Frieren" --out reports/anilist.json

Nécessite un accès Internet. Respecte la limite documentée (30 requêtes/min en mode dégradé) :
la sonde émet environ 6 requêtes.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from typing import Any, Callable

from _common import emit, environment

from aniflow.net.cache import MemoryCache
from aniflow.services.anilist import AniListClient, AniListError, AniListNotFoundError
from aniflow.services.anilist.client import ENDPOINT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", default="Sousou no Frieren", help="titre à rechercher")
    parser.add_argument("--endpoint", default=ENDPOINT, help="point d'accès GraphQL (tests locaux)")
    parser.add_argument("--max-related", type=int, default=10, help="relations animées ajoutées au test par lot")
    parser.add_argument("--out", help="fichier JSON de rapport")
    args = parser.parse_args(argv)

    client = AniListClient(endpoint=args.endpoint)
    steps: list[dict[str, Any]] = []
    state: dict[str, Any] = {}

    def step(name: str, action: Callable[[], dict[str, Any]], *, expect: type[Exception] | None = None) -> None:
        started = time.perf_counter()
        try:
            details, ok = action(), expect is None
        except AniListError as exc:
            details = {"erreur": exc.user_message, "technique": str(exc)}
            ok = expect is not None and isinstance(exc, expect)
        steps.append({"name": name, "ok": ok, "elapsed_s": round(time.perf_counter() - started, 3), "details": details, "rate_limit": str(client.last_rate_limit)})

    def search() -> dict[str, Any]:
        page = client.search_anime(args.query, per_page=5)
        state["first"] = page.items[0].id if page.items else None
        return {"total": page.total, "résultats": [{"id": i.id, "titre": i.title.display(), "format": i.format, "épisodes": i.episodes, "année": i.season_year} for i in page.items]}

    def details() -> dict[str, Any]:
        d = client.get_anime(state["first"])
        state["details"] = d
        return {"titre": d.title.display(), "id_mal": d.summary.id_mal, "relations": len(d.relations), "types_de_relation": dict(Counter(r.relation_type for r in d.relations)),
                "relations_illisibles": d.skipped_relations, "genres": list(d.summary.genres)}

    def batch() -> dict[str, Any]:
        d = state["details"]
        related = [r.node.id for r in d.relations if r.node.media_type == "ANIME"][: args.max_related]
        wanted = [d.id, *related]
        got = client.get_anime_batch(wanted)
        return {"demandées": len(wanted), "reçues": len(got), "absentes": sorted(set(wanted) - set(got))}

    def cache() -> dict[str, Any]:
        cached = AniListClient(endpoint=args.endpoint, cache=MemoryCache())
        cached.search_anime(args.query, per_page=5)
        started = time.perf_counter()
        cached.search_anime(args.query, per_page=5)
        return {"second_appel_ms": round((time.perf_counter() - started) * 1000, 2)}

    step("search", search)
    if state.get("first") is not None:
        step("details_with_relations", details)
        if "details" in state:
            step("batch_id_in", batch)
    step("cache_hit", cache)
    step("not_found_is_clean_error", lambda: client.get_anime(999_999_999), expect=AniListNotFoundError)

    report = {"tool": "anilist_probe", "ok": all(s["ok"] for s in steps) and bool(steps), **environment(), "endpoint": args.endpoint, "steps": steps}
    emit(report, args.out)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
