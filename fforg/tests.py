from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase

from .redisdb import TimersDB


class TimersDBTimeUntilTest(TestCase):
    def setUp(self):
        self.timers = TimersDB('redis://localhost:6379/0')
        self.mock_db = MagicMock()
        self.timers._conn = self.mock_db

    def test_returns_zero_and_sets_key_on_first_call(self):
        self.mock_db.get.return_value = None
        delta = timedelta(seconds=10)
        now = 1000.0

        result = self.timers.time_until('mykey', delta=delta, now=now)

        self.assertEqual(result, timedelta(seconds=0))
        self.mock_db.set.assert_called_once_with('mykey', str(now), ex=delta)

    def test_returns_remaining_time_when_delta_not_elapsed(self):
        delta = timedelta(seconds=10)
        last_called = 995.0
        now = 1000.0
        # expected = 995 + 10 = 1005, diff = 1005 - 1000 = 5
        self.mock_db.get.return_value = str(last_called).encode()

        result = self.timers.time_until('mykey', delta=delta, now=now)

        self.assertEqual(result, timedelta(seconds=5))
        self.mock_db.set.assert_not_called()

    def test_returns_zero_and_resets_key_when_delta_elapsed(self):
        delta = timedelta(seconds=10)
        last_called = 980.0
        now = 1000.0
        # expected = 980 + 10 = 990, diff = 990 - 1000 = -10 (elapsed)
        self.mock_db.get.return_value = str(last_called).encode()

        result = self.timers.time_until('mykey', delta=delta, now=now)

        self.assertEqual(result, timedelta(seconds=0))
        self.mock_db.set.assert_called_once_with('mykey', str(now), ex=delta)

    def test_returns_zero_and_resets_key_when_diff_is_exactly_zero(self):
        delta = timedelta(seconds=10)
        last_called = 990.0
        now = 1000.0
        # expected = 990 + 10 = 1000, diff = 0
        self.mock_db.get.return_value = str(last_called).encode()

        result = self.timers.time_until('mykey', delta=delta, now=now)

        self.assertEqual(result, timedelta(seconds=0))
        self.mock_db.set.assert_called_once_with('mykey', str(now), ex=delta)


class TimersDBResetTest(TestCase):
    def setUp(self):
        self.timers = TimersDB('redis://localhost:6379/0')
        self.mock_db = MagicMock()
        self.timers._conn = self.mock_db

    def test_reset_sets_key_to_now(self):
        delta = timedelta(seconds=30)
        now = 1234.5

        with patch('fforg.redisdb.time') as mock_time:
            mock_time.time.return_value = now
            self.timers.reset('mykey', delta)

        self.mock_db.set.assert_called_once_with('mykey', str(now), ex=delta)
