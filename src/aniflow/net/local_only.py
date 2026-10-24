"""Garde-fous « IA locale exclusive » : adresses et noms de modèles autorisés.

Contexte vérifié (docs.ollama.com/faq) : Ollama peut exécuter des modèles « cloud » (suffixe
-cloud) via son API locale ; le calcul se fait alors sur les serveurs d'Ollama. Appeler
http://127.0.0.1:11434 ne garantit donc pas, à lui seul, une inférence locale.
"""

from __future__ import annotations

import ipaddress
import urllib.parse
from typing import Mapping

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"


class NotLocalError(ValueError):
    """Adresse ou modèle qui sortirait de la machine locale."""

    def __init__(self, message: str, user_message: str) -> None:
        super().__init__(message)
        self.user_message = user_message


def _is_loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def validate_local_base_url(url: str) -> str:
    """Retourne l'URL normalisée (sans « / » final) ou lève NotLocalError si elle n'est pas locale."""
    refus = (
        "AniFlow n'utilise que l'IA locale : l'adresse du service IA doit être "
        "http://127.0.0.1 (ou localhost). Corrigez-la dans Paramètres > IA locale."
    )
    if not isinstance(url, str) or not url.strip():
        raise NotLocalError("adresse vide", refus)
    parts = urllib.parse.urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        raise NotLocalError(f"schéma refusé : {parts.scheme!r}", refus)
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise NotLocalError("l'adresse ne doit contenir que l'hôte et le port", refus)
    host = (parts.hostname or "").rstrip(".").lower()
    if not _is_loopback_host(host):
        raise NotLocalError(f"hôte non local refusé : {host!r}", refus)
    try:
        port = parts.port
    except ValueError as exc:
        raise NotLocalError("port invalide", refus) from exc
    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc += f":{port}"
    return f"{parts.scheme}://{netloc}"


def is_cloud_model_name(name: str) -> bool:
    lowered = (name or "").strip().lower()
    return lowered.endswith("-cloud") or lowered.endswith(":cloud")


def has_remote_markers(entry: Mapping[str, object] | None) -> bool:
    """Vrai si une entrée /api/tags ou /api/show indique un modèle exécuté à distance."""
    return bool(entry) and bool(entry.get("remote_host") or entry.get("remote_model"))


def ensure_not_cloud_name(name: str) -> None:
    if is_cloud_model_name(name):
        raise NotLocalError(
            f"modèle cloud refusé : {name!r}",
            f"Le modèle « {name} » s'exécute dans le cloud d'Ollama, pas sur votre PC. "
            "Choisissez un modèle installé localement (sans suffixe « -cloud »).",
        )
