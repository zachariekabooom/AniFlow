import logging
import threading
import unittest
from io import StringIO
from unittest import mock

from aniflow.ui.qt_logging import MAX_LOGGED_REPEATS, QtMessageRecorder, level_of


class FakeMode:
    def __init__(self, name):
        self.name = name


WARNING = FakeMode("QtWarningMsg")


class LevelTests(unittest.TestCase):
    def test_levels_follow_the_qt_message_type_name(self):
        expected = {"QtDebugMsg": logging.DEBUG, "QtInfoMsg": logging.INFO, "QtWarningMsg": logging.WARNING, "QtCriticalMsg": logging.ERROR, "QtFatalMsg": logging.CRITICAL}
        for name, level in expected.items():
            with self.subTest(name):
                self.assertEqual(level_of(FakeMode(name)), level)

    def test_qualified_and_unknown_types(self):
        self.assertEqual(level_of("QtMsgType.QtCriticalMsg"), logging.ERROR)
        for unknown in (FakeMode("autre"), None, 3):
            with self.subTest(unknown=unknown):
                self.assertEqual(level_of(unknown), logging.WARNING)


class RecorderTests(unittest.TestCase):
    def setUp(self):
        self.logger = logging.getLogger("aniflow.qt.test")
        self.recorder = QtMessageRecorder(logger=self.logger)

    def test_messages_reach_the_journal_with_their_level(self):
        with self.assertLogs("aniflow.qt.test", level="DEBUG") as captured:
            self.recorder.handle(WARNING, None, "QFont::setPointSize: Point size <= 0")
            self.recorder.handle(FakeMode("QtInfoMsg"), None, "information")
        self.assertEqual([(r.levelno, r.getMessage()) for r in captured.records], [(logging.WARNING, "QFont::setPointSize: Point size <= 0"), (logging.INFO, "information")])

    def test_style_warnings_are_singled_out(self):
        for text in ("Could not parse application stylesheet", "Unknown property text-allign", "Could not parse stylesheet of object QPushButton(0x1)"):
            self.recorder.handle(WARNING, None, text)
        self.recorder.handle(WARNING, None, "QFont::setPointSize: Point size <= 0 (-1)")  # avertissement sans rapport avec le style
        self.recorder.handle(FakeMode("QtDebugMsg"), None, "Could not parse (simple trace de débogage)")  # sous le niveau WARNING
        self.assertEqual(
            self.recorder.style_warnings(),
            ["Could not parse application stylesheet", "Unknown property text-allign", "Could not parse stylesheet of object QPushButton(0x1)"],
        )

    def test_a_repeated_message_is_throttled_in_the_journal_but_still_counted(self):
        with self.assertLogs("aniflow.qt.test", level="DEBUG") as captured:
            for _ in range(10):
                self.recorder.handle(WARNING, None, "message répété")
        self.assertEqual(len(captured.records), MAX_LOGGED_REPEATS + 1)  # N occurrences + une ligne « suite masquée »
        self.assertIn("suite est masquée", captured.records[-1].getMessage())
        self.assertEqual(len(self.recorder.messages), 10)

    def test_echo_to_stderr_only_for_warnings_and_above(self):
        recorder = QtMessageRecorder(echo_stderr=True, logger=self.logger)
        with mock.patch("sys.stderr", new=StringIO()) as stderr:
            recorder.handle(FakeMode("QtInfoMsg"), None, "info discrète")
            recorder.handle(WARNING, None, "avertissement visible")
        self.assertEqual(stderr.getvalue(), "Qt : avertissement visible\n")

    def test_the_handler_never_raises(self):
        broken = mock.MagicMock()
        broken.log.side_effect = RuntimeError("journal défaillant")
        QtMessageRecorder(logger=broken).handle(WARNING, None, "x")  # ne doit pas lever
        QtMessageRecorder().handle(object(), None, None)  # type et message inattendus

    def test_memory_is_bounded(self):
        for i in range(700):
            self.recorder.handle(FakeMode("QtDebugMsg"), None, f"message {i}")
        self.assertEqual(len(self.recorder.messages), 500)

    def test_safe_from_several_threads(self):
        def worker():
            for i in range(100):
                self.recorder.handle(WARNING, None, f"fil {i % 5}")

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(self.recorder.messages), 500)


if __name__ == "__main__":
    unittest.main()
