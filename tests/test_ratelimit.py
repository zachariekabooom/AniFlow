import threading
import unittest

from aniflow.services.anilist.ratelimit import RateLimitWouldBlock, SlidingWindowRateLimiter
from tests.support.fake_mpv import FakeClock


def make(**kwargs):
    clock = FakeClock()
    return clock, SlidingWindowRateLimiter(clock=clock.time, sleep=clock.sleep, **kwargs)


class SlidingWindowTests(unittest.TestCase):
    def test_burst_up_to_max_then_waits_for_window(self):
        clock, limiter = make(max_calls=3, period=60.0, min_interval=0.0)
        start = clock.now
        waits = [limiter.acquire() for _ in range(3)]
        self.assertEqual(waits, [0.0, 0.0, 0.0])
        waited = limiter.acquire()  # 4e appel : doit attendre la fin de la fenêtre
        self.assertAlmostEqual(waited, 60.0, places=3)
        self.assertGreaterEqual(clock.now - start, 60.0)

    def test_min_interval_spaces_calls(self):
        clock, limiter = make(max_calls=30, period=60.0, min_interval=0.5)
        limiter.acquire()
        self.assertAlmostEqual(limiter.acquire(), 0.5, places=3)

    def test_penalize_blocks_everyone(self):
        clock, limiter = make(max_calls=30, period=60.0, min_interval=0.0)
        limiter.penalize(45.0)
        self.assertAlmostEqual(limiter.acquire(), 45.0, places=3)

    def test_max_wait_raises_without_sleeping(self):
        clock, limiter = make(max_calls=1, period=60.0, min_interval=0.0)
        limiter.acquire()
        before = clock.now
        with self.assertRaises(RateLimitWouldBlock) as ctx:
            limiter.acquire(max_wait=1.0)
        self.assertAlmostEqual(ctx.exception.wait, 60.0, places=3)
        self.assertEqual(clock.now, before)

    def test_window_slides(self):
        clock, limiter = make(max_calls=2, period=10.0, min_interval=0.0)
        limiter.acquire()
        clock.sleep(6)
        limiter.acquire()
        clock.sleep(5)  # le premier appel (t=0) est sorti de la fenêtre de 10 s
        self.assertEqual(limiter.acquire(), 0.0)

    def test_invalid_parameters(self):
        for kwargs in ({"max_calls": 0}, {"period": 0}, {"min_interval": -1}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                SlidingWindowRateLimiter(**kwargs)

    def test_threads_never_exceed_quota(self):
        limiter = SlidingWindowRateLimiter(max_calls=5, period=60.0, min_interval=0.0)
        granted, refused = [], []

        def worker():
            try:
                limiter.acquire(max_wait=0)
                granted.append(1)
            except RateLimitWouldBlock:
                refused.append(1)

        threads = [threading.Thread(target=worker) for _ in range(25)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual((len(granted), len(refused)), (5, 20))


if __name__ == "__main__":
    unittest.main()
