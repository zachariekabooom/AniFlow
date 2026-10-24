"""Sonde de faisabilité libmpv : démarrage, lecture réelle, pause, seek ±15 s, reprise de position.

La logique est séparée du module « mpv » (injecté) pour être testée avec un faux lecteur ; la
validation réelle de libmpv se fait sous Windows avec tools/phase0/mpv_probe.py.
"""

from __future__ import annotations

import os
import platform
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, MutableMapping


@dataclass
class Check:
    name: str
    ok: bool
    details: dict[str, Any] = field(default_factory=dict)


def prepare_dll_search_path(dll_dir: str | None, environ: MutableMapping[str, str] = os.environ) -> str | None:
    """Rend libmpv-2.dll trouvable : python-mpv cherche dans %PATH% (ordre de recherche de ctypes)."""
    if not dll_dir:
        return None
    directory = os.path.abspath(dll_dir)
    environ["PATH"] = directory + os.pathsep + environ.get("PATH", "")
    add_dll_directory = getattr(os, "add_dll_directory", None)  # Windows uniquement
    if add_dll_directory and os.path.isdir(directory):  # lève OSError si le dossier n'existe pas
        try:
            add_dll_directory(directory)
        except OSError:
            pass  # %PATH% est déjà complété : c'est lui que python-mpv consulte
    return directory


def _wait_until(predicate: Callable[[], bool], timeout: float, sleep: Callable[[float], None], clock: Callable[[], float], interval: float = 0.05) -> bool:
    deadline = clock() + timeout
    while clock() < deadline:
        if predicate():
            return True
        sleep(interval)
    return bool(predicate())


def _safe(getter: Callable[[], Any]) -> Any:
    try:
        return getter()
    except Exception:  # propriété indisponible selon la version de libmpv
        return None


def _new_player(mpv_module: Any, headless: bool, log_lines: list[str], **extra: Any) -> Any:
    def log_handler(level: str, prefix: str, text: str) -> None:
        if len(log_lines) < 40:
            log_lines.append(f"[{level}] {prefix}: {text.strip()}")

    options: dict[str, Any] = {"log_handler": log_handler, "loglevel": "warn", **extra}
    if headless:
        options.update(vo="null", ao="null", input_default_bindings=False, osc=False)
    return mpv_module.MPV(**options)


def run_probe(
    mpv_module: Any,
    media_path: str,
    *,
    headless: bool = True,
    play_seconds: float = 3.0,
    seek_seconds: float = 15.0,
    tolerance: float = 1.5,
    startup_timeout: float = 15.0,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    checks: list[Check] = []
    log_lines: list[str] = []
    versions: dict[str, Any] = {}
    media: dict[str, Any] = {"path": media_path}
    resume_pos: float | None = None
    player = None

    def pos() -> float | None:
        return player.time_pos

    try:
        player = _new_player(mpv_module, headless, log_lines)
        versions = {"mpv_version": _safe(lambda: player.mpv_version), "ffmpeg_version": _safe(lambda: player.ffmpeg_version)}

        t0 = clock()
        player.play(media_path)
        started = _wait_until(lambda: pos() is not None, startup_timeout, sleep, clock)
        duration = _safe(lambda: player.duration)
        media["duration_s"] = duration
        checks.append(Check("load_and_start", started, {"startup_s": round(clock() - t0, 3), "duration_s": duration}))
        if not started:
            raise RuntimeError("la lecture n'a pas démarré (voir mpv_log)")
        duration = duration or float("inf")

        before = pos()
        sleep(play_seconds)
        advanced = pos() - before
        checks.append(Check("playback_advances_in_real_time", abs(advanced - play_seconds) <= tolerance, {"expected_s": play_seconds, "measured_s": round(advanced, 3)}))

        player.pause = True
        sleep(0.4)
        p0 = pos()
        sleep(2.0)
        p1 = pos()
        checks.append(Check("pause_freezes_position", player.pause is True and abs(p1 - p0) < 0.25, {"drift_s": round(p1 - p0, 3), "pause_property": player.pause}))

        before = pos()
        player.seek(seek_seconds, reference="relative", precision="exact")
        sleep(0.6)
        after = pos()
        expected = min(before + seek_seconds, duration)
        checks.append(Check("seek_forward_15s", abs(after - expected) <= tolerance, {"before_s": round(before, 3), "after_s": round(after, 3), "expected_s": round(expected, 3)}))

        before = pos()
        player.seek(-seek_seconds, reference="relative", precision="exact")
        sleep(0.6)
        after = pos()
        expected = max(before - seek_seconds, 0.0)
        checks.append(Check("seek_backward_15s", abs(after - expected) <= tolerance, {"before_s": round(before, 3), "after_s": round(after, 3), "expected_s": round(expected, 3)}))

        target = min(30.0, duration / 2 if duration != float("inf") else 30.0)
        player.seek(target, reference="absolute", precision="exact")
        sleep(0.6)
        resume_pos = pos()
        checks.append(Check("seek_absolute_and_read_position", abs(resume_pos - target) <= tolerance, {"target_s": target, "read_s": round(resume_pos, 3)}))
    except Exception as exc:  # une panne de la sonde est un résultat, pas un plantage
        checks.append(Check("probe_exception", False, {"error": repr(exc)}))
    finally:
        if player is not None:
            _safe(player.terminate)

    if resume_pos is not None:
        resumed = None
        try:
            player = _new_player(mpv_module, headless, log_lines, start=f"{resume_pos:.3f}", pause=True)
            player.play(media_path)
            _wait_until(lambda: player.time_pos is not None, startup_timeout, sleep, clock)
            resumed = player.time_pos
            checks.append(Check("resume_from_saved_position", resumed is not None and abs(resumed - resume_pos) <= tolerance, {"saved_s": round(resume_pos, 3), "resumed_s": None if resumed is None else round(resumed, 3)}))
        except Exception as exc:
            checks.append(Check("resume_from_saved_position", False, {"error": repr(exc)}))
        finally:
            if player is not None:
                _safe(player.terminate)

    return {
        "tool": "mpv_probe",
        "ok": bool(checks) and all(c.ok for c in checks),
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": {"system": platform.platform(), "python": sys.version.split()[0], "machine": platform.machine()},
        "mode": "headless (vo=null, ao=null)" if headless else "fenêtre mpv autonome",
        "libmpv": versions,
        "media": media,
        "checks": [asdict(c) for c in checks],
        "mpv_log": log_lines,
    }
