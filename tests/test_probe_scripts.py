"""Exécute réellement les scripts de tools/phase0 (sous-processus) contre des serveurs locaux factices."""

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.support import fixtures
from tests.support.servers import FakeHttpServer, FakeResponse
from tests.test_ollama_client import router as ollama_router

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "phase0"


def run_script(name, *args, timeout=90):
    return subprocess.run([sys.executable, str(TOOLS / name), *args], capture_output=True, text=True, encoding="utf-8", timeout=timeout, cwd=ROOT)


def anilist_router(request):
    body = request.json()
    query, variables = body["query"], body["variables"]
    if "id_in" in query:
        return FakeResponse(200, fixtures.batch_response(list(variables["ids"])))
    if "Media(id" in query:
        if variables["id"] == 999_999_999:
            return FakeResponse(404, {"data": {"Media": None}, "errors": [{"message": "Not Found.", "status": 404}]})
        return FakeResponse(200, fixtures.details_response(variables["id"]))
    return FakeResponse(200, fixtures.search_response([1001, 1002]))


class AniListProbeScript(unittest.TestCase):
    def test_full_run_against_local_fake(self):
        with FakeHttpServer(anilist_router) as server:
            result = run_script("anilist_probe.py", "--endpoint", server.url, "--query", "test")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        report = json.loads(result.stdout)
        steps = {s["name"]: s for s in report["steps"]}
        self.assertEqual(list(steps), ["search", "details_with_relations", "batch_id_in", "cache_hit", "not_found_is_clean_error"])
        self.assertTrue(all(s["ok"] for s in steps.values()))
        self.assertEqual(steps["batch_id_in"]["details"], {"demandées": 3, "reçues": 3, "absentes": []})  # la source MANGA n'est pas demandée
        self.assertEqual(steps["details_with_relations"]["details"]["relations_illisibles"], 1)
        self.assertLess(steps["cache_hit"]["details"]["second_appel_ms"], 50)

    def test_unreachable_endpoint_gives_a_failing_report_not_a_crash(self):
        result = run_script("anilist_probe.py", "--endpoint", "http://127.0.0.1:9")
        self.assertEqual(result.returncode, 1)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertIn("connexion Internet", report["steps"][0]["details"]["erreur"])


class OllamaProbeScript(unittest.TestCase):
    def test_full_run_against_local_fake(self):
        with FakeHttpServer(ollama_router()) as server:
            result = run_script("ollama_probe.py", "--url", server.url, "--model", "gemma4:e2b")
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        steps = {s["name"]: s for s in json.loads(result.stdout)["steps"]}
        self.assertEqual(list(steps), ["version", "modèles_installés", "état_du_modèle", "modalités", "génération_structurée", "mémoire_en_cours"])
        self.assertTrue(steps["modalités"]["details"]["audio"])
        self.assertEqual(steps["génération_structurée"]["details"]["jetons_par_seconde"], 50.0)
        flagged = {m["nom"]: m["distant_donc_interdit"] for m in steps["modèles_installés"]["details"]["modèles"]}
        self.assertTrue(flagged["gpt-oss:120b-cloud"])

    def test_non_local_url_is_refused_without_any_request(self):
        result = run_script("ollama_probe.py", "--url", "http://example.com:11434")
        self.assertEqual(result.returncode, 1)
        step = json.loads(result.stdout)["steps"][0]
        self.assertEqual(step["name"], "adresse_locale")
        self.assertFalse(step["ok"])

    def test_cloud_model_is_refused_and_never_generates(self):
        with FakeHttpServer(ollama_router()) as server:
            result = run_script("ollama_probe.py", "--url", server.url, "--model", "gpt-oss:120b-cloud")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("/api/chat", [r.path for r in server.requests])
        self.assertNotIn("/api/show", [r.path for r in server.requests])


class MediaAndPlayerScripts(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg absent")
    def test_make_test_media_creates_a_playable_synthetic_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "t.mp4"
            result = run_script("make_test_media.py", "--out", str(out), "--seconds", "3")
            self.assertEqual(result.returncode, 0, result.stderr)
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(out)], capture_output=True, text=True)
            info = json.loads(probe.stdout)
            self.assertAlmostEqual(float(info["format"]["duration"]), 3.0, delta=0.6)
            self.assertEqual({s["codec_type"] for s in info["streams"]}, {"video", "audio"})
            self.assertLess(out.stat().st_size, 300_000)

    @unittest.skipIf(importlib.util.find_spec("mpv") is not None, "python-mpv installé : la sonde réelle s'exécuterait")
    def test_mpv_probe_explains_missing_module(self):
        result = run_script("mpv_probe.py", "--file", "x.mp4")
        self.assertEqual(result.returncode, 2)
        self.assertIn("pip install mpv", result.stderr)

    def test_missing_dll_dir_is_explained(self):
        for script in ("mpv_probe.py", "qt_smoke.py"):
            with self.subTest(script=script):
                args = ("--file", "x.mp4", "--dll-dir", "dossier-absent") if script == "mpv_probe.py" else ("--dll-dir", "dossier-absent")
                result = run_script(script, *args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("Dossier introuvable", result.stderr)

    @unittest.skipIf(importlib.util.find_spec("PySide6") is not None, "PySide6 installé : la fenêtre s'ouvrirait")
    def test_qt_smoke_explains_missing_pyside6(self):
        result = run_script("qt_smoke.py")
        self.assertEqual(result.returncode, 2)
        self.assertIn("pip install PySide6", result.stderr)


if __name__ == "__main__":
    unittest.main()
