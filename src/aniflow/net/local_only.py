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


_IPV4_LOOPBACK = ipaddress.ip_network("127.0.0.0/8")
_IPV6_LOOPBACK = ipaddress.IPv6Address("::1")


def _canonical_loopback_host(host: str) -> str | None:
    """Forme canonique d'un hôte de bouclage, ou None si l'hôte n'en est pas un.

    Liste blanche explicite, jamais ipaddress.is_loopback : sa sémantique pour les adresses IPv4-mappées
    (::ffff:127.0.0.1) a changé entre correctifs de CPython (False en 3.12.3, True en 3.12.10). Sont acceptés :
    le nom « localhost », une IPv4 en notation décimale pointée stricte dans 127.0.0.0/8, et ::1. Tout le reste
    est refusé : IPv4-mappée ou compatible, NAT64/6to4, zone IPv6, écritures décimale/hexadécimale/octale/abrégée,
    point final et noms DNS (dont la résolution échappe à AniFlow). Le client se connecte à la forme renvoyée ici.
    """
    if host == "localhost":
        return host
    if "%" in host:  # zone IPv6 (::1%lo)
        return None
    try:
        v4 = ipaddress.IPv4Address(host)
    except ValueError:
        pass
    else:
        return str(v4) if v4 in _IPV4_LOOPBACK else None
    try:
        v6 = ipaddress.IPv6Address(host)
    except ValueError:
        return None
    return str(v6) if v6 == _IPV6_LOOPBACK else None


def validate_local_base_url(url: str) -> str:
    """Retourne l'URL canonique (sans « / » final) ou lève NotLocalError si elle n'est pas strictement locale."""
    refus = (
        "AniFlow n'utilise que l'IA locale : l'adresse du service IA doit être "
        "http://127.0.0.1 (ou localhost). Corrigez-la dans Paramètres > IA locale."
    )
    if not isinstance(url, str) or not url.strip():
        raise NotLocalError("adresse vide", refus)
    try:
        parts = urllib.parse.urlsplit(url.strip())
        port = parts.port
    except ValueError as exc:  # crochets invalides, IPv4 entre crochets, port hors limites…
        raise NotLocalError(f"adresse invalide : {exc}", refus) from exc
    if parts.scheme not in ("http", "https"):
        raise NotLocalError(f"schéma refusé : {parts.scheme!r}", refus)
    if parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        raise NotLocalError("l'adresse ne doit contenir que l'hôte et le port", refus)
    host = _canonical_loopback_host(parts.hostname or "")
    if host is None or ("[" in parts.netloc) != (":" in host):  # les crochets n'entourent que de l'IPv6
        raise NotLocalError(f"hôte non local refusé : {parts.hostname!r}", refus)
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
