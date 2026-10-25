"""Serveur HTTP local scriptable : teste le vrai transport sans accès Internet.

Politique des erreurs du serveur (identique sous Linux et Windows) :
- un client qui coupe volontairement la connexion (délai dépassé, réponse refusée car trop grosse) provoque
  BrokenPipeError/ConnectionResetError sous Linux mais ConnectionAbortedError (WinError 10053) sous Windows.
  Ces déconnexions ne sont tolérées que si le test le déclare (tolerate_client_abort=True) ; elles sont comptées ;
- toute autre exception d'un gestionnaire (ou une déconnexion non déclarée) fait échouer le test à la sortie du
  « with », au lieu de n'être qu'une trace sur stderr ;
- à la sortie, le serveur attend la fin des réponses en cours : les compteurs sont alors définitifs.
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time
import traceback
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

_WINSOCK_ABORTED_OR_RESET = (10053, 10054)  # WSAECONNABORTED, WSAECONNRESET


def _is_client_abort(exc: BaseException | None) -> bool:
    return isinstance(exc, ConnectionError) or getattr(exc, "winerror", None) in _WINSOCK_ABORTED_OR_RESET


@dataclass
class RecordedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes

    def json(self) -> Any:
        return json.loads(self.body.decode("utf-8")) if self.body else None


@dataclass
class FakeResponse:
    status: int = 200
    body: Any = None  # dict/list -> JSON ; str/bytes -> brut
    headers: dict[str, str] = field(default_factory=dict)
    delay: float = 0.0


class FakeHttpServer:
    def __init__(self, responder: Callable[[RecordedRequest], FakeResponse], *, tolerate_client_abort: bool = False) -> None:
        self.requests: list[RecordedRequest] = []
        self.aborted_responses = 0  # déconnexions du client tolérées (déclarées par le test)
        self.errors: list[str] = []  # tout le reste : fait échouer le test à la sortie
        self._lock = threading.Lock()
        outer = self

        class Handler(BaseHTTPRequestHandler):
            timeout = 5  # un client bloqué ne doit jamais figer la suite de tests

            def _handle(self) -> None:
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                request = RecordedRequest(self.command, self.path, {k.lower(): v for k, v in self.headers.items()}, body)
                outer.requests.append(request)
                response = responder(request)
                if response.delay:
                    time.sleep(response.delay)
                payload = response.body
                if isinstance(payload, (dict, list)):
                    data = json.dumps(payload).encode("utf-8")
                elif isinstance(payload, str):
                    data = payload.encode("utf-8")
                else:
                    data = payload or b""
                self.send_response(response.status)
                for key, value in response.headers.items():
                    self.send_header(key, value)
                if "Content-Type" not in response.headers:
                    self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = _handle

            def log_message(self, *args: Any) -> None:
                pass

        class Server(ThreadingHTTPServer):
            daemon_threads = False  # server_close() attend les réponses en cours

            def handle_error(self, request: Any, client_address: Any) -> None:
                error = sys.exc_info()[1]
                with outer._lock:
                    if tolerate_client_abort and _is_client_abort(error):
                        outer.aborted_responses += 1
                    else:
                        outer.errors.append(traceback.format_exc())

        self._server = Server(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeHttpServer":
        self._thread.start()
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self._server.shutdown()
        self._server.server_close()  # attend les gestionnaires encore en cours (réponses retardées)
        if exc_type is None and self.errors:  # n'écrase jamais l'échec du test lui-même
            raise AssertionError("exception inattendue dans le serveur de test :\n" + "\n---\n".join(self.errors))


def scripted(*responses: FakeResponse) -> Callable[[RecordedRequest], FakeResponse]:
    """Répond dans l'ordre ; au-delà du scénario, renvoie une erreur 500 explicite."""
    queue = list(responses)

    def responder(_: RecordedRequest) -> FakeResponse:
        return queue.pop(0) if queue else FakeResponse(500, {"errors": [{"message": "scénario épuisé"}]})

    return responder


def closed_port_url() -> str:
    """URL locale sur laquelle rien n'écoute (connexion refusée immédiatement)."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return f"http://127.0.0.1:{port}"
