"""Utilitaires partagés par les sondes de la phase 0 (scripts de développement, pas du code applicatif)."""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

def force_utf8_output() -> None:
    """Impose l'UTF-8 sur stdout/stderr, quelle que soit la page de code de la console.

    Sous Windows un tube (redirection, sous-processus) hérite de la page de code ANSI (cp1252 en français) :
    sans cela « Vidéo créée » sort en 0xE9 et tout lecteur UTF-8 échoue. stdout reste strict (une erreur
    d'encodage doit se voir) ; stderr utilise backslashreplace pour qu'un diagnostic ne plante jamais.
    """
    for stream, errors in ((sys.stdout, "strict"), (sys.stderr, "backslashreplace")):
        reconfigure = getattr(stream, "reconfigure", None)  # absent si la sortie est None (pythonw) ou remplacée
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors=errors)


force_utf8_output()  # effet voulu à l'import : tout script qui importe _common émet de l'UTF-8


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
