"""Exécute réellement les scripts de tools/phase0 (sous-processus) contre des serveurs locaux factices."""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

from tests.support import fixtures
from tests.support.servers import FakeHttpServer, FakeResponse
from tests.test_ollama_client import router as ollama_router

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "phase0"


# Sous Windows, un tube hérite de la page de code ANSI (cp1252 en français), pas de l'UTF-8. On simule cette console
# pour TOUS les sous-processus, sur n'importe quel système : chaque test vérifie donc aussi l'encodage de sortie.
CONSOLE_ENV = {**os.environ, "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}


@dataclass
class ScriptResult:
    returncode: int
    stdout: str
    stderr: str


def _decode_utf8(script, stream, data):
    """Décodage strict dans le thread du test : une sortie non UTF-8 fait ÉCHOUER le test (avec contexte)."""
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        around = data[max(0, exc.start - 20) : exc.end + 20]
        raise AssertionError(
            f"{script} : {stream} n'est pas de l'UTF-8 valide ({exc.reason}, octet {data[exc.start]:#04x} à la position "
            f"{exc.start}) ; contexte : {around!r}. Le script doit forcer la sortie UTF-8 (voir tools/phase0/_common.py)."
        ) from None


def run_script(name, *args, timeout=90):
    done = subprocess.run([sys.executable, str(TOOLS / name), *args], capture_output=True, timeout=timeout, cwd=ROOT, env=CONSOLE_ENV)
    return ScriptResult(done.returncode, _decode_utf8(name, "stdout", done.stdout), _decode_utf8(name, "stderr", done.stderr))


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


class ConsoleEncodingTests(unittest.TestCase):
    """Chaque script de tools/phase0 émet de l'UTF-8 valide même si la console du système est en cp1252."""

    # script -> (arguments d'un parcours rapide sans dépendance externe, code de retour attendu, fragment accentué attendu)
    QUICK_PATHS = {
        "anilist_probe.py": (("--endpoint", "http://127.0.0.1:9"), 1, "Vérifiez"),
        "make_test_media.py": (("--ffmpeg", "ffmpeg-inexistant-xyz"), 2, "précisez"),
        "mpv_probe.py": (("--file", "x.mp4", "--dll-dir", "dossier-absent"), 2, "Créez-le"),
        "ollama_probe.py": (("--url", "http://example.com:11434"), 1, "IA locale"),
        "qt_smoke.py": (("--dll-dir", "dossier-absent"), 2, "Créez-le"),
    }

    def test_every_script_has_a_quick_path(self):
        scripts = {p.name for p in TOOLS.glob("*.py") if not p.name.startswith("_")}
        self.assertEqual(scripts, set(self.QUICK_PATHS), "nouveau script dans tools/phase0 : ajoutez-le à QUICK_PATHS")

    def test_french_output_is_valid_utf8_with_a_cp1252_console(self):
        for name, (args, code, fragment) in self.QUICK_PATHS.items():
            with self.subTest(script=name):
                result = run_script(name, *args)  # lève AssertionError si une sortie n'est pas de l'UTF-8
                text = result.stdout + result.stderr
                self.assertEqual(result.returncode, code, text)
                self.assertIn(fragment, text)
                self.assertTrue(any(ord(c) > 127 for c in text), "ce parcours doit produire des accents, sinon il ne prouve rien")


class MediaAndPlayerScripts(unittest.TestCase):
    @unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "FFmpeg absent")
    def test_make_test_media_creates_a_playable_synthetic_video(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "t.mp4"
            result = run_script("make_test_media.py", "--out", str(out), "--seconds", "3")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Vidéo de test créée", result.stdout)  # message accentué : prouve l'UTF-8 de bout en bout
            probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration", "-of", "json", str(out)], capture_output=True)
            info = json.loads(probe.stdout.decode("utf-8"))
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
