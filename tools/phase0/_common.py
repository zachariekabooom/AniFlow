"""Utilitaires partagés par les sondes de la phase 0 (scripts de développement, pas du code applicatif)."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

for _stream in (sys.stdout, sys.stderr):  # accents et symboles corrects même hors console UTF-8
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def environment() -> dict[str, Any]:
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "machine": platform.machine(),
    }


def emit(report: dict[str, Any], out: str | None) -> None:
    text = json.dumps(report, ensure_ascii=False, indent=2)
    print(text)
    if out:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        print(f"\nRapport écrit dans : {path}", file=sys.stderr)
