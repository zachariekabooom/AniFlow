import os
import unittest

from aniflow.services.player.probe import prepare_dll_search_path, run_probe
from tests.support.fake_mpv import FakeClock, FakeMpvModule


def run(**module_kwargs):
    clock = FakeClock()
    module = FakeMpvModule(clock, **module_kwargs)
    report = run_probe(module, "test.mp4", sleep=clock.sleep, clock=clock.time)
    return report, module, {c["name"]: c for c in report["checks"]}


class ProbeLogicTests(unittest.TestCase):
    def test_healthy_player_passes_every_check(self):
        report, module, checks = run()
        self.assertTrue(report["ok"], report["checks"])
        self.assertEqual(
            list(checks),
            ["load_and_start", "playback_advances_in_real_time", "pause_freezes_position", "seek_forward_15s", "seek_backward_15s", "seek_absolute_and_read_position", "resume_from_saved_position"],
        )
        self.assertTrue(all(p.terminated for p in module.players))
        self.assertEqual(report["libmpv"]["mpv_version"], "mpv 0.fake")
        self.assertEqual(report["media"]["duration_s"], 60.0)

    def test_headless_options_are_used_and_resume_uses_saved_position(self):
        report, module, checks = run()
        first, second = module.players
        self.assertEqual((first.kwargs["vo"], first.kwargs["ao"]), ("null", "null"))
        self.assertEqual(float(second.kwargs["start"]), checks["seek_absolute_and_read_position"]["details"]["read_s"])
        self.assertTrue(second.kwargs["pause"])

    def test_pause_that_does_not_stop_the_clock_is_detected(self):
        report, _, checks = run(pause_broken=True)
        self.assertFalse(report["ok"])
        self.assertFalse(checks["pause_freezes_position"]["ok"])

    def test_seek_that_does_nothing_is_detected(self):
        report, _, checks = run(seek_broken=True)
        self.assertFalse(report["ok"])
        self.assertFalse(checks["seek_forward_15s"]["ok"])

    def test_playback_that_never_starts_is_reported_not_raised(self):
        clock = FakeClock()
        module = FakeMpvModule(clock)
        module.MPV = lambda **kw: type("Dead", (), {"time_pos": None, "duration": None, "terminate": lambda self: None, "play": lambda self, p: None, "mpv_version": "x", "ffmpeg_version": "y"})()
        report = run_probe(module, "absent.mp4", sleep=clock.sleep, clock=clock.time, startup_timeout=1.0)
        self.assertFalse(report["ok"])
        self.assertEqual([c["name"] for c in report["checks"]], ["load_and_start", "probe_exception"])


class DllPathTests(unittest.TestCase):
    def test_prepends_directory_to_path(self):
        env = {"PATH": "/usr/bin"}
        directory = prepare_dll_search_path("third_party/libmpv", env)
        self.assertTrue(env["PATH"].startswith(directory + os.pathsep))
        self.assertTrue(env["PATH"].endswith("/usr/bin"))

    def test_missing_directory_never_raises(self):
        env = {"PATH": "x"}
        prepare_dll_search_path("dossier/qui/n/existe/pas", env)  # add_dll_directory (Windows) lèverait sans garde
        self.assertIn("existe", env["PATH"])

    def test_none_leaves_environment_untouched(self):
        env = {"PATH": "/usr/bin"}
        self.assertIsNone(prepare_dll_search_path(None, env))
        self.assertEqual(env, {"PATH": "/usr/bin"})


if __name__ == "__main__":
    unittest.main()
