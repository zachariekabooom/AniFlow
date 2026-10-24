import json
import unittest

from aniflow.net.local_only import validate_local_base_url
from aniflow.net.transport import UrllibTransport
from aniflow.services.ai import (
    AICapabilityError,
    AIModelMissingError,
    AINotLocalError,
    AIResponseError,
    AIUnavailableError,
    OllamaClient,
)
from aniflow.services.ai.ollama_client import (
    CAP_AUDIO,
    STATE_MODEL_MISSING,
    STATE_NO_MODEL,
    STATE_NOT_LOCAL,
    STATE_READY,
    STATE_UNAVAILABLE,
)
from tests.support.fake_mpv import FakeClock
from tests.support.servers import FakeHttpServer, FakeResponse, closed_port_url

INSTALLED = {"gemma4:e2b", "gemma4:e4b", "texte-seul:latest"}
TAGS = {
    "models": [
        {"name": "gemma4:e2b", "model": "gemma4:e2b", "size": 7_200_000_000, "digest": "abc", "details": {"family": "gemma4", "parameter_size": "5.1B", "quantization_level": "Q4_K_M"}},
        {"name": "gpt-oss:120b-cloud", "model": "gpt-oss:120b-cloud", "remote_model": "gpt-oss:120b", "remote_host": "https://ollama.com:443", "size": 384, "details": {}},
        {"name": "autre:latest", "remote_host": "https://ollama.com:443", "size": 1, "details": {}},  # distant sans suffixe
    ]
}


def router(*, capabilities=("completion", "vision", "audio", "thinking"), chat=None, show_extra=None, omit_capabilities=False):
    def responder(req):
        if req.path == "/api/version":
            return FakeResponse(200, {"version": "0.30.0"})
        if req.path == "/api/tags":
            return FakeResponse(200, TAGS)
        if req.path == "/api/ps":
            return FakeResponse(200, {"models": [{"name": "gemma4:e2b", "size": 7_000_000_000, "size_vram": 3_900_000_000}]})
        if req.path == "/api/show":
            name = req.json()["model"]
            if name not in INSTALLED:
                return FakeResponse(404, {"error": f"model '{name}' not found"})
            caps = ("completion",) if name == "texte-seul:latest" else capabilities
            body = {"details": {"family": "gemma4", "parameter_size": "5.1B", "quantization_level": "Q4_K_M"}, "model_info": {"gemma4.context_length": 131072}}
            if not omit_capabilities:
                body["capabilities"] = list(caps)
            body.update(show_extra or {})
            return FakeResponse(200, body)
        if req.path == "/api/chat":
            if chat is not None:
                return chat(req)
            return FakeResponse(200, {"model": req.json()["model"], "message": {"role": "assistant", "content": '{"answer": "ok"}'},
                                      "total_duration": 2_500_000_000, "load_duration": 500_000_000, "prompt_eval_count": 20, "eval_count": 50, "eval_duration": 1_000_000_000})
        return FakeResponse(404, {"error": "inconnu"})

    return responder


class ExplodingTransport:
    def __init__(self):
        self.calls = 0

    def request(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("aucun appel réseau n'aurait dû avoir lieu")


def client_for(server, **kwargs):
    return OllamaClient(server.url, transport=UrllibTransport(use_system_proxy=False), **kwargs)


class LocalOnlyUrlTests(unittest.TestCase):
    def test_non_local_addresses_are_refused(self):
        for url in ("http://example.com:11434", "http://192.168.1.10:11434", "http://0.0.0.0:11434", "ftp://127.0.0.1", "http://user:pw@127.0.0.1:11434",
                    "http://127.0.0.1:11434/v1", "", "   ", "http://127.0.0.1:99999", "http://localhost.evil.test", "http://[::ffff:127.0.0.1]:11434", "https://ollama.com"):
            with self.subTest(url=url), self.assertRaises(AINotLocalError):
                OllamaClient(url, transport=ExplodingTransport())

    def test_loopback_addresses_are_accepted_and_normalised(self):
        self.assertEqual(validate_local_base_url("http://LOCALHOST:11434/"), "http://localhost:11434")
        self.assertEqual(validate_local_base_url("http://127.0.0.5:8000"), "http://127.0.0.5:8000")
        self.assertEqual(validate_local_base_url("http://[::1]:11434"), "http://[::1]:11434")
        self.assertEqual(OllamaClient("http://127.0.0.1:11434", transport=ExplodingTransport()).base_url, "http://127.0.0.1:11434")


class CloudModelGuardTests(unittest.TestCase):
    def test_cloud_names_are_refused_before_any_network_call(self):
        transport = ExplodingTransport()
        client = OllamaClient(transport=transport)
        for name in ("gpt-oss:120b-cloud", "gemma4:31b-cloud", "x:cloud", "MODELE-CLOUD"):
            with self.subTest(name=name):
                with self.assertRaises(AINotLocalError) as ctx:
                    client.show(name)
                self.assertIn("cloud", ctx.exception.user_message)
                with self.assertRaises(AINotLocalError):
                    client.chat_json(name, [{"role": "user", "content": "x"}])
                self.assertEqual(client.check_ready(name).state, STATE_NOT_LOCAL)
        self.assertEqual(transport.calls, 0)

    def test_remote_markers_in_show_are_refused(self):
        with FakeHttpServer(router(show_extra={"remote_host": "https://ollama.com:443"})) as server:
            with self.assertRaises(AINotLocalError):
                client_for(server).show("gemma4:e2b")

    def test_listing_flags_remote_models(self):
        with FakeHttpServer(router()) as server:
            entries = {e.name: e for e in client_for(server).list_models()}
        self.assertFalse(entries["gemma4:e2b"].is_remote)
        self.assertEqual((entries["gemma4:e2b"].parameter_size, entries["gemma4:e2b"].quantization), ("5.1B", "Q4_K_M"))
        self.assertTrue(entries["gpt-oss:120b-cloud"].is_remote)
        self.assertTrue(entries["autre:latest"].is_remote)

    def test_redirect_is_never_followed(self):
        with FakeHttpServer(lambda r: FakeResponse(302, "", {"Location": "http://example.invalid/api/version"})) as server:
            with self.assertRaises(AINotLocalError):
                client_for(server).version()
        self.assertEqual(len(server.requests), 1)


class DiagnosticsTests(unittest.TestCase):
    def test_version_models_running(self):
        with FakeHttpServer(router()) as server:
            client = client_for(server)
            self.assertEqual(client.version(), "0.30.0")
            running = client.running()
        self.assertEqual((running[0].name, running[0].size_vram_bytes), ("gemma4:e2b", 3_900_000_000))

    def test_show_parses_capabilities_and_context(self):
        with FakeHttpServer(router()) as server:
            info = client_for(server).show("gemma4:e2b")
        self.assertEqual(info.capabilities, frozenset({"completion", "vision", "audio", "thinking"}))
        self.assertTrue(info.supports("vision"))
        self.assertEqual(info.context_length, 131072)

    def test_missing_model_message_never_downloads(self):
        with FakeHttpServer(router()) as server:
            with self.assertRaises(AIModelMissingError) as ctx:
                client_for(server).show("inconnu:1b")
        self.assertIn("ollama pull inconnu:1b", ctx.exception.user_message)
        self.assertIn("jamais", ctx.exception.user_message)

    def test_unreachable_server_message(self):
        client = OllamaClient(closed_port_url(), transport=UrllibTransport(use_system_proxy=False))
        with self.assertRaises(AIUnavailableError) as ctx:
            client.version()
        self.assertIn("Aucune bascule vers un service distant", ctx.exception.user_message)

    def test_check_ready_states(self):
        with FakeHttpServer(router()) as server:
            client = client_for(server)
            ready = client.check_ready("gemma4:e2b")
            self.assertEqual((ready.state, ready.ok, ready.version), (STATE_READY, True, "0.30.0"))
            self.assertIn("vision", ready.capabilities)
            self.assertEqual(client.check_ready(None).state, STATE_NO_MODEL)
            self.assertEqual(client.check_ready("inconnu:1b").state, STATE_MODEL_MISSING)
        down = OllamaClient(closed_port_url(), transport=UrllibTransport(use_system_proxy=False)).check_ready("gemma4:e2b")
        self.assertEqual((down.state, down.ok), (STATE_UNAVAILABLE, False))
        self.assertIn("Ollama", down.message)


class CapabilityTests(unittest.TestCase):
    def test_require_capability(self):
        with FakeHttpServer(router()) as server:
            client = client_for(server)
            client.require_capability("gemma4:e2b", CAP_AUDIO)
            with self.assertRaises(AICapabilityError):
                client.require_capability("texte-seul:latest", CAP_AUDIO)

    def test_unknown_capabilities_fail_closed(self):
        with FakeHttpServer(router(omit_capabilities=True)) as server:
            with self.assertRaises(AICapabilityError) as ctx:
                client_for(server).require_capability("gemma4:e2b", "vision")
        self.assertIn("inconnues", str(ctx.exception))

    def test_images_need_vision_and_nothing_is_sent_otherwise(self):
        with FakeHttpServer(router()) as server:
            client = client_for(server)
            with self.assertRaises(AICapabilityError):
                client.chat_json("texte-seul:latest", [{"role": "user", "content": "décris", "images": ["AAAA"]}])
            self.assertNotIn("/api/chat", [r.path for r in server.requests])
            client.chat_json("gemma4:e2b", [{"role": "user", "content": "décris", "images": ["AAAA"]}])
            self.assertIn("/api/chat", [r.path for r in server.requests])

    def test_audio_and_video_keys_are_refused_by_this_client(self):
        with FakeHttpServer(router()) as server:
            client = client_for(server)
            for key in ("audio", "videos"):
                with self.subTest(key=key), self.assertRaises(AICapabilityError):
                    client.chat_json("gemma4:e2b", [{"role": "user", "content": "x", key: ["AAAA"]}])
            self.assertNotIn("/api/chat", [r.path for r in server.requests])


class ChatTests(unittest.TestCase):
    def test_structured_chat_and_metrics(self):
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
        with FakeHttpServer(router()) as server:
            result = client_for(server).chat_json("gemma4:e2b", [{"role": "user", "content": "Dis ok"}], schema=schema, options={"temperature": 0, "num_ctx": 4096}, think=False, keep_alive="2m")
            payload = [r for r in server.requests if r.path == "/api/chat"][0].json()
        self.assertEqual(result.data, {"answer": "ok"})
        self.assertAlmostEqual(result.metrics.tokens_per_second, 50.0)
        self.assertEqual((result.metrics.prompt_tokens, result.metrics.completion_tokens), (20, 50))
        self.assertAlmostEqual(result.metrics.load_seconds, 0.5)
        self.assertEqual((payload["stream"], payload["format"], payload["options"], payload["keep_alive"]), (False, schema, {"temperature": 0, "num_ctx": 4096}, "2m"))
        self.assertIs(payload["think"], False)

    def test_think_is_only_sent_when_supported(self):
        with FakeHttpServer(router(capabilities=("completion",))) as server:
            client_for(server).chat_json("gemma4:e2b", [{"role": "user", "content": "x"}], think=True)
            payload = [r for r in server.requests if r.path == "/api/chat"][0].json()
        self.assertNotIn("think", payload)
        self.assertEqual(payload["format"], "json")

    def test_invalid_or_empty_model_output(self):
        def chat(content):
            return lambda req: FakeResponse(200, {"message": {"role": "assistant", "content": content}})

        for content in ("ceci n'est pas du JSON", "   "):
            with self.subTest(content=content), FakeHttpServer(router(chat=chat(content))) as server:
                with self.assertRaises(AIResponseError):
                    client_for(server).chat_json("gemma4:e2b", [{"role": "user", "content": "x"}])

    def test_server_error_detail_is_surfaced(self):
        detail = "model requires more system memory (9.0 GiB) than is available (6.1 GiB)"
        with FakeHttpServer(router(chat=lambda r: FakeResponse(500, {"error": detail}))) as server:
            with self.assertRaises(AIResponseError) as ctx:
                client_for(server).chat_json("gemma4:e2b", [{"role": "user", "content": "x"}])
        self.assertIn("9.0 GiB", ctx.exception.user_message)

    def test_invalid_messages(self):
        with FakeHttpServer(router()) as server:
            client = client_for(server)
            for messages in ([], [{"role": "robot", "content": "x"}], [{"role": "user", "content": 3}]):
                with self.subTest(messages=messages), self.assertRaises(ValueError):
                    client.chat_json("gemma4:e2b", messages)

    def test_verification_is_cached_for_a_short_time(self):
        clock = FakeClock()
        with FakeHttpServer(router()) as server:
            client = client_for(server, verify_ttl=60.0, clock=clock.time)
            for _ in range(2):
                client.chat_json("gemma4:e2b", [{"role": "user", "content": "x"}])
            self.assertEqual([r.path for r in server.requests].count("/api/show"), 1)
            clock.sleep(61)
            client.chat_json("gemma4:e2b", [{"role": "user", "content": "x"}])
            self.assertEqual([r.path for r in server.requests].count("/api/show"), 2)


class NoDownloadTests(unittest.TestCase):
    def test_client_only_uses_read_and_generate_endpoints(self):
        with FakeHttpServer(router()) as server:
            client = client_for(server)
            client.version(); client.list_models(); client.running(); client.check_ready("gemma4:e2b")
            client.chat_json("gemma4:e2b", [{"role": "user", "content": "x"}])
            with self.assertRaises(AIModelMissingError):
                client.show("inconnu:1b")
        allowed = {"/api/version", "/api/tags", "/api/ps", "/api/show", "/api/chat"}
        self.assertLessEqual({r.path for r in server.requests}, allowed)
        self.assertFalse(hasattr(client, "pull"))


if __name__ == "__main__":
    unittest.main()
