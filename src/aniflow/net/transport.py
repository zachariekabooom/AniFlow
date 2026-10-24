"""Transport HTTP minimal fondé sur la bibliothèque standard (aucune dépendance externe)."""

from __future__ import annotations

import http.client
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Mapping, Protocol

DEFAULT_MAX_BYTES = 16 * 1024 * 1024


class TransportError(Exception):
    """Échec de communication : réseau coupé, connexion refusée, délai dépassé…"""

    def __init__(self, message: str, *, is_timeout: bool = False) -> None:
        super().__init__(message)
        self.is_timeout = is_timeout


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]  # noms en minuscules
    body: bytes

    def header(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name.lower(), default)


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 15.0,
    ) -> HttpResponse: ...


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Ne suit jamais une redirection : la réponse 3xx est renvoyée telle quelle."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _is_timeout(reason: object) -> bool:
    return isinstance(reason, (socket.timeout, TimeoutError)) or "timed out" in str(reason).lower()


class UrllibTransport:
    """Transport synchrone (à appeler depuis un thread de travail, jamais depuis l'UI).

    use_system_proxy=False ignore les proxys du système : exigé pour les appels à l'IA
    locale, qui ne doivent jamais transiter par un intermédiaire.
    """

    def __init__(self, *, use_system_proxy: bool = True, max_bytes: int = DEFAULT_MAX_BYTES) -> None:
        handlers: list[urllib.request.BaseHandler] = [_NoRedirect()]
        if not use_system_proxy:
            handlers.append(urllib.request.ProxyHandler({}))
        self._opener = urllib.request.build_opener(*handlers)
        self._max_bytes = max_bytes

    def request(
        self,
        method: str,
        url: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float = 15.0,
    ) -> HttpResponse:
        req = urllib.request.Request(url, data=body, method=method.upper(), headers=dict(headers or {}))
        try:
            with self._opener.open(req, timeout=timeout) as resp:
                return self._to_response(resp.status, resp.headers, resp)
        except urllib.error.HTTPError as exc:  # statut 4xx/5xx (et 3xx non suivi)
            try:
                return self._to_response(exc.code, exc.headers, exc)
            finally:
                exc.close()
        except urllib.error.URLError as exc:
            raise TransportError(str(exc.reason), is_timeout=_is_timeout(exc.reason)) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise TransportError("délai dépassé", is_timeout=True) from exc
        except (OSError, http.client.HTTPException) as exc:
            raise TransportError(str(exc), is_timeout=_is_timeout(exc)) from exc

    def _to_response(self, status: int, headers, fp) -> HttpResponse:
        data = fp.read(self._max_bytes + 1)
        if len(data) > self._max_bytes:
            raise TransportError("réponse trop volumineuse")
        return HttpResponse(status, {k.lower(): v for k, v in headers.items()}, data)
