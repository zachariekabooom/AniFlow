import json
import unittest

from aniflow.net.cache import MemoryCache
from aniflow.net.transport import HttpResponse, TransportError, UrllibTransport
from aniflow.services.anilist import (
    AniListClient,
    AniListGraphQLError,
    AniListHttpError,
    AniListNetworkError,
    AniListNotFoundError,
    AniListRateLimitError,
    AniListResponseError,
    AniListTimeoutError,
)
from aniflow.services.anilist.client import RateLimitInfo
from aniflow.services.anilist.ratelimit import SlidingWindowRateLimiter
from tests.support import fixtures
from tests.support.fake_mpv import FakeClock
from tests.support.servers import FakeHttpServer, FakeResponse, closed_port_url, scripted


def ok(payload, headers=None):
    return HttpResponse(200, {k.lower(): v for k, v in (headers or {}).items()}, json.dumps(payload).encode())


def reply(status, payload=None, headers=None):
    body = b"" if payload is None else json.dumps(payload).encode()
    return HttpResponse(status, {k.lower(): v for k, v in (headers or {}).items()}, body)


class ScriptedTransport:
    def __init__(self, *items):
        self.items = list(items)
        self.calls = []

    def request(self, method, url, *, body=None, headers=None, timeout=15.0):
        self.calls.append({"method": method, "url": url, "json": json.loads(body) if body else None, "headers": dict(headers or {}), "timeout": timeout})
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def make_client(*items, **kwargs):
    clock = FakeClock()
    sleeps = []
    limiter = SlidingWindowRateLimiter(30, 60.0, 0.0, clock=clock.time, sleep=clock.sleep)
    transport = ScriptedTransport(*items)
    client = AniListClient(transport, limiter=limiter, sleep=sleeps.append, **kwargs)
    return client, transport, clock, sleeps


class RequestShapeTests(unittest.TestCase):
    def test_search_hides_adult_by_default(self):
        client, transport, *_ = make_client(ok(fixtures.search_response([1, 2])))
        page = client.search_anime("  frieren ")
        call = transport.calls[0]
        self.assertEqual([i.id for i in page.items], [1, 2])
        self.assertEqual(call["json"]["variables"], {"search": "frieren", "page": 1, "perPage": 10, "isAdult": False})
        self.assertIn("$isAdult", call["json"]["query"])
        self.assertEqual(call["method"], "POST")
        self.assertEqual(call["headers"]["Content-Type"], "application/json")
        self.assertTrue(call["headers"]["User-Agent"].startswith("AniFlow/"))

    def test_search_including_adult_sends_no_filter(self):
        client, transport, *_ = make_client(ok(fixtures.search_response([1])))
        client.search_anime("x", include_adult=True)
        call = transport.calls[0]
        self.assertNotIn("isAdult", call["json"]["variables"])
        self.assertNotIn("$isAdult", call["json"]["query"])  # le champ isAdult reste demandé, pas filtré
        self.assertNotIn("isAdult:", call["json"]["query"])

    def test_empty_search_makes_no_request(self):
        client, transport, *_ = make_client()
        self.assertEqual(client.search_anime("   ").items, ())
        self.assertEqual(transport.calls, [])

    def test_paging_is_clamped(self):
        client, transport, *_ = make_client(ok(fixtures.search_response([])))
        client.search_anime("x", page=-3, per_page=500)
        variables = transport.calls[0]["json"]["variables"]
        self.assertEqual((variables["page"], variables["perPage"]), (1, 50))

    def test_invalid_ids_rejected_before_any_request(self):
        client, transport, *_ = make_client()
        for bad in (0, -1, "5", True, None):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                client.get_anime(bad)
        with self.assertRaises(ValueError):
            client.get_anime_batch([1, 0])
        self.assertEqual(transport.calls, [])


class CacheTests(unittest.TestCase):
    def test_second_identical_call_is_served_from_cache(self):
        client, transport, *_ = make_client(ok(fixtures.search_response([1])), cache=MemoryCache())
        a = client.search_anime("x")
        b = client.search_anime("x")
        self.assertEqual(a, b)
        self.assertEqual(len(transport.calls), 1)

    def test_different_parameters_do_not_share_cache(self):
        client, transport, *_ = make_client(ok(fixtures.search_response([1])), ok(fixtures.search_response([2])), cache=MemoryCache())
        client.search_anime("x")
        client.search_anime("x", page=2)
        self.assertEqual(len(transport.calls), 2)

    def test_errors_are_never_cached(self):
        client, transport, *_ = make_client(reply(404, {"errors": [{"message": "Not Found."}]}), ok(fixtures.details_response(1001)), cache=MemoryCache())
        with self.assertRaises(AniListNotFoundError):
            client.get_anime(1001)
        self.assertEqual(client.get_anime(1001).id, 1001)


class ErrorMappingTests(unittest.TestCase):
    def test_http_404_is_not_found(self):
        client, *_ = make_client(reply(404, {"data": {"Media": None}, "errors": [{"message": "Not Found.", "status": 404}]}))
        with self.assertRaises(AniListNotFoundError) as ctx:
            client.get_anime(999)
        self.assertIn("introuvable", ctx.exception.user_message)

    def test_null_media_is_not_found(self):
        client, *_ = make_client(ok({"data": {"Media": None}}))
        with self.assertRaises(AniListNotFoundError):
            client.get_anime(999)

    def test_http_400_is_graphql_error_with_messages(self):
        client, *_ = make_client(reply(400, {"errors": [{"message": "Cannot query field \"foo\""}]}))
        with self.assertRaises(AniListGraphQLError) as ctx:
            client.search_anime("x")
        self.assertIn("foo", ctx.exception.messages[0])

    def test_graphql_errors_with_null_data(self):
        client, *_ = make_client(ok({"data": None, "errors": [{"message": "boom"}]}))
        with self.assertRaises(AniListGraphQLError):
            client.search_anime("x")

    def test_invalid_json_and_missing_data(self):
        client, *_ = make_client(HttpResponse(200, {}, b"<html>oups</html>"), ok({"pas": "de data"}))
        with self.assertRaises(AniListResponseError):
            client.search_anime("x")
        with self.assertRaises(AniListResponseError):
            client.search_anime("y")

    def test_network_and_timeout_errors(self):
        client, *_ = make_client(TransportError("connexion refusée"), TransportError("délai dépassé", is_timeout=True))
        with self.assertRaises(AniListNetworkError) as net:
            client.search_anime("x")
        self.assertIn("connexion Internet", net.exception.user_message)
        with self.assertRaises(AniListTimeoutError):
            client.search_anime("y")

    def test_unexpected_status_and_redirect(self):
        client, *_ = make_client(reply(403, {"errors": [{"message": "interdit"}]}), reply(302, None, {"Location": "http://ailleurs"}))
        with self.assertRaises(AniListHttpError) as ctx:
            client.search_anime("x")
        self.assertEqual(ctx.exception.status, 403)
        with self.assertRaises(AniListHttpError) as ctx:
            client.search_anime("y")
        self.assertEqual(ctx.exception.status, 302)


class RetryTests(unittest.TestCase):
    def test_429_waits_retry_after_then_succeeds(self):
        client, transport, clock, _ = make_client(reply(429, {"errors": [{"message": "Too Many Requests."}]}, {"Retry-After": "7"}), ok(fixtures.search_response([1])))
        start = clock.now
        self.assertEqual(len(client.search_anime("x").items), 1)
        self.assertEqual(len(transport.calls), 2)
        self.assertGreaterEqual(clock.now - start, 7.0)

    def test_429_longer_than_max_wait_raises_and_keeps_penalty(self):
        client, transport, clock, _ = make_client(reply(429, None, {"Retry-After": "60"}))
        with self.assertRaises(AniListRateLimitError) as ctx:
            client.search_anime("x")
        self.assertEqual(ctx.exception.retry_after, 60.0)
        self.assertIn("60 s", ctx.exception.user_message)
        self.assertEqual(len(transport.calls), 1)
        before = clock.now
        with self.assertRaises(AniListRateLimitError):  # la pénalité partagée bloque l'appel suivant sans requête
            client.search_anime("y")
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(clock.now, before)

    def test_5xx_is_retried_with_backoff(self):
        client, transport, _, sleeps = make_client(reply(503), reply(500), ok(fixtures.search_response([1])))
        self.assertEqual(len(client.search_anime("x").items), 1)
        self.assertEqual(sleeps, [1, 2])
        self.assertEqual(len(transport.calls), 3)

    def test_5xx_gives_up_after_retries(self):
        client, transport, _, sleeps = make_client(reply(500), reply(500), reply(502, {"errors": [{"message": "bad gateway"}]}))
        with self.assertRaises(AniListHttpError) as ctx:
            client.search_anime("x")
        self.assertEqual(ctx.exception.status, 502)
        self.assertEqual(len(transport.calls), 3)

    def test_rate_limit_headers_are_recorded(self):
        client, *_ = make_client(ok(fixtures.search_response([1]), {"X-RateLimit-Limit": "90", "X-RateLimit-Remaining": "59"}))
        client.search_anime("x")
        self.assertEqual(client.last_rate_limit, RateLimitInfo(90, 59))


class DetailsAndBatchTests(unittest.TestCase):
    def test_get_anime_details(self):
        client, transport, *_ = make_client(ok(fixtures.details_response(1001)))
        details = client.get_anime(1001)
        self.assertEqual(details.id, 1001)
        self.assertEqual(len(details.relations), 3)
        self.assertEqual(transport.calls[0]["json"]["variables"], {"id": 1001})
        self.assertIn("relationType(version: 2)", transport.calls[0]["json"]["query"])

    def test_batch_chunks_by_50_and_dedupes(self):
        ids = list(range(1, 121)) + [5, 6]  # 120 identifiants uniques + 2 doublons
        client, transport, *_ = make_client(
            ok(fixtures.batch_response(list(range(1, 51)))),
            ok(fixtures.batch_response(list(range(51, 101)))),
            ok(fixtures.batch_response(list(range(101, 121)))),
        )
        result = client.get_anime_batch(ids)
        self.assertEqual(len(transport.calls), 3)
        self.assertEqual([c["json"]["variables"]["perPage"] for c in transport.calls], [50, 50, 20])
        self.assertEqual(len(result), 120)
        self.assertIn("id_in: $ids", transport.calls[0]["json"]["query"])

    def test_batch_missing_ids_are_simply_absent(self):
        client, *_ = make_client(ok(fixtures.batch_response([10])))
        result = client.get_anime_batch([10, 11])
        self.assertEqual(set(result), {10})


class RealTransportTests(unittest.TestCase):
    """Le vrai transport urllib contre un serveur HTTP local (aucun accès Internet)."""

    def client_for(self, server, **kwargs):
        clock = FakeClock()
        limiter = SlidingWindowRateLimiter(30, 60.0, 0.0, clock=clock.time, sleep=clock.sleep)
        return AniListClient(UrllibTransport(use_system_proxy=False), endpoint=server.url, limiter=limiter, **kwargs)

    def test_search_roundtrip_over_http(self):
        with FakeHttpServer(scripted(FakeResponse(200, fixtures.search_response([1, 2])))) as server:
            page = self.client_for(server).search_anime("test")
        self.assertEqual([i.id for i in page.items], [1, 2])
        request = server.requests[0]
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.headers["content-type"], "application/json")
        self.assertEqual(request.json()["variables"]["search"], "test")

    def test_429_headers_survive_real_http(self):
        responses = scripted(FakeResponse(429, {"errors": [{"message": "Too Many Requests."}]}, {"Retry-After": "3"}), FakeResponse(200, fixtures.search_response([9])))
        with FakeHttpServer(responses) as server:
            page = self.client_for(server).search_anime("x")
        self.assertEqual(page.items[0].id, 9)
        self.assertEqual(len(server.requests), 2)

    def test_redirect_is_not_followed(self):
        with FakeHttpServer(scripted(FakeResponse(302, "", {"Location": "http://example.invalid/"}))) as server:
            with self.assertRaises(AniListHttpError) as ctx:
                self.client_for(server).search_anime("x")
        self.assertEqual(ctx.exception.status, 302)
        self.assertEqual(len(server.requests), 1)

    def test_connection_refused_is_a_clean_network_error(self):
        client = AniListClient(UrllibTransport(use_system_proxy=False), endpoint=closed_port_url())
        with self.assertRaises(AniListNetworkError) as ctx:
            client.search_anime("x")
        self.assertNotIsInstance(ctx.exception, AniListTimeoutError)

    def test_slow_server_times_out(self):
        # Le client coupe volontairement la connexion : le serveur de test tolère (et compte) cette déconnexion.
        with FakeHttpServer(scripted(FakeResponse(200, fixtures.search_response([1]), delay=0.6)), tolerate_client_abort=True) as server:
            with self.assertRaises(AniListTimeoutError):
                self.client_for(server, timeout=0.2).search_anime("x")

    def test_oversized_response_is_refused(self):
        with FakeHttpServer(scripted(FakeResponse(200, b"x" * 5000)), tolerate_client_abort=True) as server:  # le client abandonne
            client = AniListClient(UrllibTransport(use_system_proxy=False, max_bytes=1000), endpoint=server.url)
            with self.assertRaises(AniListNetworkError):
                client.search_anime("x")


if __name__ == "__main__":
    unittest.main()
