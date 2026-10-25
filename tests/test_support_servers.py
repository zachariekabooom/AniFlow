"""Le serveur HTTP de test lui-même : politique des déconnexions du client (WinError 10053 incluse)."""

import http.server
import time
import unittest
from unittest import mock

from aniflow.net.transport import TransportError, UrllibTransport
from tests.support.servers import FakeHttpServer, FakeResponse

# Erreur exacte observée sous Windows quand le client a déjà coupé la connexion (simulée à l'identique ici).
WINDOWS_ABORT = ConnectionAbortedError(10053, "Une connexion établie a été abandonnée par un logiciel de votre ordinateur hôte")


def get(server, timeout=2.0):
    try:
        UrllibTransport(use_system_proxy=False).request("GET", server.url, timeout=timeout)
    except TransportError:
        pass  # le client voit une connexion fermée : c'est l'effet recherché


def abort_while_writing():
    return mock.patch.object(http.server.BaseHTTPRequestHandler, "end_headers", side_effect=WINDOWS_ABORT)


class ClientAbortPolicyTests(unittest.TestCase):
    def test_declared_abort_is_counted_and_not_reported(self):
        with abort_while_writing(), FakeHttpServer(lambda r: FakeResponse(200, {}), tolerate_client_abort=True) as server:
            get(server)
        self.assertEqual((server.aborted_responses, server.errors), (1, []))

    def test_undeclared_abort_fails_the_test_instead_of_printing_a_trace(self):
        with self.assertRaises(AssertionError) as ctx:
            with abort_while_writing(), FakeHttpServer(lambda r: FakeResponse(200, {})) as server:
                get(server)
        self.assertIn("ConnectionAbortedError", str(ctx.exception))
        self.assertEqual(server.aborted_responses, 0)

    def test_other_exceptions_are_never_swallowed_even_when_aborts_are_tolerated(self):
        def broken(request):
            raise ValueError("bug du test")

        with self.assertRaises(AssertionError) as ctx:
            with FakeHttpServer(broken, tolerate_client_abort=True) as server:
                get(server)
        self.assertIn("bug du test", str(ctx.exception))
        self.assertEqual(server.aborted_responses, 0)

    def test_a_failure_inside_the_with_block_is_not_masked(self):
        with self.assertRaises(RuntimeError):
            with FakeHttpServer(lambda r: FakeResponse(200, {})):
                raise RuntimeError("échec du test lui-même")

    def test_exit_waits_for_slow_responses_so_results_are_final(self):
        started = time.monotonic()
        with FakeHttpServer(lambda r: FakeResponse(200, {}, delay=0.4), tolerate_client_abort=True) as server:
            with self.assertRaises(TransportError):
                UrllibTransport(use_system_proxy=False).request("GET", server.url, timeout=0.1)
        self.assertGreaterEqual(time.monotonic() - started, 0.35)  # le gestionnaire retardé est attendu
        self.assertEqual(server.errors, [])


if __name__ == "__main__":
    unittest.main()
