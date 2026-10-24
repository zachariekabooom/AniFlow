"""Serveur HTTP local scriptable : teste le vrai transport sans accès Internet."""

from __future__ import annotations

import json
import socket
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable


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
    def __init__(self, responder: Callable[[RecordedRequest], FakeResponse]) -> None:
        self.requests: list[RecordedRequest] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
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
                try:
                    self.send_response(response.status)
                    for key, value in response.headers.items():
                        self.send_header(key, value)
                    if "Content-Type" not in response.headers:
                        self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            do_GET = do_POST = _handle

            def log_message(self, *args: Any) -> None:
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._server.daemon_threads = True
        self._thread = threading.Thread(target=self._server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def __enter__(self) -> "FakeHttpServer":
        self._thread.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self._server.shutdown()
        self._server.server_close()


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
