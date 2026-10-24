"""Faux module « mpv » à horloge simulée : teste la logique de la sonde sans libmpv."""

from __future__ import annotations

from typing import Any


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class FakePlayer:
    def __init__(self, module: "FakeMpvModule", **kwargs: Any) -> None:
        self._module = module
        self.kwargs = kwargs
        self._pos: float | None = None
        self._pause = bool(kwargs.get("pause", False))
        self._last = module.clock.time()
        self.terminated = False
        self.mpv_version = "mpv 0.fake"
        self.ffmpeg_version = "fake-ffmpeg"

    def _advance(self) -> None:
        now = self._module.clock.time()
        running = not self._pause or self._module.pause_broken
        if self._pos is not None and running:
            self._pos = min(self._module.duration, self._pos + (now - self._last))
        self._last = now

    def play(self, path: str) -> None:
        self._module.played.append(path)
        self._pos = float(self.kwargs.get("start", 0) or 0)
        self._last = self._module.clock.time()

    @property
    def time_pos(self) -> float | None:
        self._advance()
        return self._pos

    @property
    def duration(self) -> float:
        return self._module.duration

    @property
    def pause(self) -> bool:
        return self._pause

    @pause.setter
    def pause(self, value: bool) -> None:
        self._advance()
        self._pause = bool(value)

    def seek(self, amount: float, reference: str = "relative", precision: str = "default") -> None:
        self._advance()
        if self._module.seek_broken:
            return
        base = self._pos or 0.0
        target = base + amount if reference == "relative" else amount
        self._pos = max(0.0, min(self._module.duration, target))

    def terminate(self) -> None:
        self.terminated = True


class FakeMpvModule:
    def __init__(self, clock: FakeClock, *, duration: float = 60.0, pause_broken: bool = False, seek_broken: bool = False) -> None:
        self.clock = clock
        self.duration = duration
        self.pause_broken = pause_broken
        self.seek_broken = seek_broken
        self.players: list[FakePlayer] = []
        self.played: list[str] = []

    def MPV(self, **kwargs: Any) -> FakePlayer:  # noqa: N802 — même nom que python-mpv
        player = FakePlayer(self, **kwargs)
        self.players.append(player)
        return player
