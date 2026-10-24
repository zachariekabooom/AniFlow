"""Journalisation dans un fichier tournant (jamais de secrets ni de données personnelles dans les messages)."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_HANDLER_NAME = "aniflow-file"


def setup_logging(logs_dir: Path, *, level: int = logging.INFO) -> Path:
    """Configure le logger « aniflow » (idempotent) et retourne le chemin du fichier journal."""
    logs_dir = Path(logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / "aniflow.log"
    logger = logging.getLogger("aniflow")
    logger.setLevel(level)
    for handler in list(logger.handlers):
        if handler.get_name() == _HANDLER_NAME:
            logger.removeHandler(handler)
            handler.close()
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s : %(message)s"))
    logger.addHandler(handler)
    return log_path
