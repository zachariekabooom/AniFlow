"""Hygiène des fichiers SUIVIS par Git (dépôt public) : ni base, ni binaire, ni secret, ni chemin personnel.

Ne regarde que l'index courant (`git ls-files`). Il n'examine PAS l'historique : un fichier retiré de l'index
n'est plus signalé, quoi qu'il ait contenu auparavant.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path, PurePosixPath

FORBIDDEN_SUFFIXES = (
    ".db", ".db-wal", ".db-shm", ".sqlite", ".sqlite3",  # bases personnelles
    ".dll", ".exe",  # binaires (libmpv…)
    ".gguf", ".safetensors",  # modèles IA
    ".mp4", ".mkv", ".avi", ".mov", ".webm",  # médias
    ".zip", ".7z",  # archives de livraison
    ".part", ".tmp", ".log", ".pyc",
)
FORBIDDEN_TOP_DIRS = frozenset({"reports", "third_party", "models", "media", "videos", "downloads", "cache", "logs", ".venv", "venv"})
ALLOWED_EXACT = frozenset({"reports/README.md", "third_party/README.md"})
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_SCAN_BYTES = 1024 * 1024
THIS_FILE = "tests/support/repo_hygiene.py"

# Les motifs à capture sont ignorés quand le « corps » est un faux jeton (peu de caractères distincts : xxxx, 0000…).
SECRET_PATTERNS = {
    "jeton GitHub": re.compile(r"\bgh[pousr]_([A-Za-z0-9]{36,})\b"),
    "jeton GitHub à granularité fine": re.compile(r"\bgithub_pat_([A-Za-z0-9_]{50,})\b"),
    "clé API de type sk-": re.compile(r"\bsk-(?:ant-)?([A-Za-z0-9_-]{20,})\b"),
    "clé AWS": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    "jeton Slack": re.compile(r"\bxox[abprs]-([A-Za-z0-9-]{10,})\b"),
    "clé privée": re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
}
PERSONAL_PATH = re.compile(r"[A-Za-z]:\\Users\\(?![<%$])[^\\\s\"'`]+|/home/[a-z][a-z0-9_-]*/|/Users/[A-Za-z][A-Za-z0-9_-]*/")


class RepoUnavailable(RuntimeError):
    """Git absent, ou dossier qui n'est pas (ou n'est pas lisible comme) un dépôt Git."""


def tracked_files(root: Path) -> list[str]:
    git = shutil.which("git")
    if not git:
        raise RepoUnavailable("git est introuvable")
    try:
        done = subprocess.run([git, "-C", str(root), "ls-files", "-z"], capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepoUnavailable(str(exc)) from exc
    if done.returncode != 0:
        raise RepoUnavailable(done.stderr.decode("utf-8", "replace").strip() or "git ls-files a échoué")
    return [os.fsdecode(raw) for raw in done.stdout.split(b"\0") if raw]


def _path_problems(rel: str) -> list[str]:
    if rel in ALLOWED_EXACT:
        return []
    parts = PurePosixPath(rel).parts
    name = parts[-1]
    problems = []
    if rel.lower().endswith(FORBIDDEN_SUFFIXES):
        problems.append("type de fichier interdit (base, binaire, modèle, média, archive ou journal)")
    if len(parts) > 1 and parts[0].lower() in FORBIDDEN_TOP_DIRS:
        problems.append("dossier réservé aux fichiers locaux")
    if "__pycache__" in parts:
        problems.append("cache Python")
    if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
        problems.append("fichier d'environnement (secrets possibles)")
    return problems


def _content_problems(text: str) -> list[str]:
    problems = []
    for number, line in enumerate(text.splitlines(), 1):
        for label, pattern in SECRET_PATTERNS.items():
            for found in pattern.finditer(line):
                body = found.group(1) if found.groups() else None
                if body is not None and len(set(body)) < 10:
                    continue
                problems.append(f"ligne {number} : {label}")
        if PERSONAL_PATH.search(line):
            problems.append(f"ligne {number} : chemin personnel")
    return problems


def find_violations(root: Path) -> list[str]:
    """Une ligne par problème, sans jamais reproduire le secret ni le chemin trouvés."""
    problems = []
    for rel in tracked_files(root):
        problems += [f"{rel} : {reason}" for reason in _path_problems(rel)]
        path = root / rel
        try:
            size = path.stat().st_size
        except OSError:
            continue  # supprimé de l'arbre de travail mais encore dans l'index
        if size > MAX_FILE_BYTES:
            problems.append(f"{rel} : fichier de {size / 1_048_576:.1f} Mo (limite {MAX_FILE_BYTES // 1_048_576} Mo)")
        if size > MAX_SCAN_BYTES or rel == THIS_FILE or rel in ALLOWED_EXACT:
            continue
        data = path.read_bytes()
        if b"\0" in data[:8000]:
            continue  # binaire : pas de recherche de texte
        problems += [f"{rel} : {reason}" for reason in _content_problems(data.decode("utf-8", "replace"))]
    return problems
