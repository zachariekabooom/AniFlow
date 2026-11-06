"""Lancement d'AniFlow en sous-processus, dans les conditions d'une console Windows en français.

Un tube Windows hérite de la page de code ANSI (cp1252), pas de l'UTF-8 : on simule cette console sur tous les systèmes.
Les sorties sont capturées en octets et décodées STRICTEMENT par le test (un texte non UTF-8 fait échouer le test).
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"


@dataclass
class Result:
    returncode: int
    stdout: str
    stderr: str


def decode_utf8(label: str, stream: str, data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        around = data[max(0, exc.start - 20) : exc.end + 20]
        raise AssertionError(f"{label} : {stream} n'est pas de l'UTF-8 valide ({exc.reason}) ; contexte : {around!r}") from None


def run_python(*args: str, home: Path | None = None, code: str | None = None, timeout: float = 90.0) -> Result:
    """`python -m aniflow *args`, ou `python -c code` ; ANIFLOW_HOME = home (jamais le dossier de données réel)."""
    env = {
        **os.environ,
        "PYTHONIOENCODING": "cp1252",
        "PYTHONUTF8": "0",
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONPATH": os.pathsep.join(filter(None, [str(SRC), os.environ.get("PYTHONPATH", "")])),
    }
    env.pop("ANIFLOW_HOME", None)
    if home is not None:
        env["ANIFLOW_HOME"] = str(home)
    command = [sys.executable, "-c", code] if code else [sys.executable, "-m", "aniflow", *args]
    done = subprocess.run(command, capture_output=True, env=env, cwd=ROOT, timeout=timeout)
    label = "aniflow " + " ".join(args)
    return Result(done.returncode, decode_utf8(label, "stdout", done.stdout), decode_utf8(label, "stderr", done.stderr))
