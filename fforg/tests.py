import importlib
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.test import TestCase

from .permissions import GROUP_DEFINITIONS, seed_permission_groups
from .redisdb import HttpCacheDB, TimersDB


class SeedPermissionGroupsTest(TestCase):
    def setUp(self):
        seed_permission_groups()

    def test_creates_all_defined_groups(self):
        for name in GROUP_DEFINITIONS:
            self.assertTrue(Group.objects.filter(name=name).exists(), f"Group '{name}' not created")

    def test_all_defined_permissions_assigned(self):
        standard = {'add', 'change', 'delete', 'view'}
        for group_name, permission_list in GROUP_DEFINITIONS.items():
            group = Group.objects.get(name=group_name)
            codenames = set(group.permissions.values_list('codename', flat=True))
            for app_label, model_name, actions in permission_list:
                for action in actions:
                    codename = f'{action}_{model_name}' if action in standard else action
                    self.assertIn(
                        codename, codenames,
                        f"Group '{group_name}' missing permission '{app_label}.{codename}'"
                    )

    def test_idempotent_when_called_twice(self):
        seed_permission_groups()
        self.assertEqual(
            Group.objects.filter(name__in=GROUP_DEFINITIONS).count(),
            len(GROUP_DEFINITIONS),
        )

    def test_groups_do_not_share_key_field_permissions(self):
        # Superstream and Livestream managers should not have each other's field permission
        ss_group = Group.objects.get(name='Superstream Key Manager')
        ls_group = Group.objects.get(name='Livestream Key Manager')
        ss_codenames = set(ss_group.permissions.values_list('codename', flat=True))
        ls_codenames = set(ls_group.permissions.values_list('codename', flat=True))
        self.assertNotIn('set_key_livestream', ss_codenames)
        self.assertNotIn('set_key_superstream', ls_codenames)


class CeleryImportsTest(TestCase):
    def test_all_celery_imports_are_importable(self):
        for module in settings.CELERY_IMPORTS:
            with self.subTest(module=module):
                importlib.import_module(module)


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
        # Key was set 5 seconds ago; with a 10-second delta it should not expire for another 5 seconds
        self.mock_db.get.return_value = str(last_called).encode()

        result = self.timers.time_until('mykey', delta=delta, now=now)

        self.assertEqual(result, timedelta(seconds=5))
        self.mock_db.set.assert_not_called()

    def test_returns_zero_and_resets_key_when_delta_elapsed(self):
        delta = timedelta(seconds=10)
        last_called = 980.0
        now = 1000.0
        # Key was set 20 seconds ago, well past the 10-second delta - should return zero and reset
        self.mock_db.get.return_value = str(last_called).encode()

        result = self.timers.time_until('mykey', delta=delta, now=now)

        self.assertEqual(result, timedelta(seconds=0))
        self.mock_db.set.assert_called_once_with('mykey', str(now), ex=delta)

    def test_returns_zero_and_resets_key_when_diff_is_exactly_zero(self):
        delta = timedelta(seconds=10)
        last_called = 990.0
        now = 1000.0
        # Key was set exactly 10 seconds ago, right at the boundary - should still return zero and reset
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


class HttpCacheDBParseMaxAgeTest(TestCase):
    def test_returns_timedelta_for_valid_max_age(self):
        result = HttpCacheDB._parse_max_age('max-age=300')
        self.assertEqual(result, timedelta(seconds=300))

    def test_returns_timedelta_from_multi_directive_cache_control(self):
        result = HttpCacheDB._parse_max_age('public, max-age=600, must-revalidate')
        self.assertEqual(result, timedelta(seconds=600))

    def test_returns_none_when_max_age_is_absent(self):
        result = HttpCacheDB._parse_max_age('no-cache, no-store')
        self.assertIsNone(result)

    def test_returns_none_for_empty_string(self):
        result = HttpCacheDB._parse_max_age('')
        self.assertIsNone(result)

    def test_returns_none_when_max_age_value_is_not_an_integer(self):
        result = HttpCacheDB._parse_max_age('max-age=abc')
        self.assertIsNone(result)


class HttpCacheDBStoreTest(TestCase):
    def setUp(self):
        self.cache = HttpCacheDB('redis://localhost:6379/0')
        self.mock_db = MagicMock()
        self.cache._conn = self.mock_db

    def test_stores_etag_with_default_ttl_when_no_cache_control(self):
        self.cache.store('https://example.com/api', {'ETag': '"abc123"'})

        self.mock_db.set.assert_called_once_with(
            self.cache.make_key('etag', url='https://example.com/api'),
            '"abc123"',
            ex=HttpCacheDB.DEFAULT_TTL,
        )

    def test_stores_last_modified_with_default_ttl_when_no_cache_control(self):
        self.cache.store('https://example.com/api', {'Last-Modified': 'Tue, 01 Jan 2030 00:00:00 GMT'})

        self.mock_db.set.assert_called_once_with(
            self.cache.make_key('lm', url='https://example.com/api'),
            'Tue, 01 Jan 2030 00:00:00 GMT',
            ex=HttpCacheDB.DEFAULT_TTL,
        )

    def test_uses_cache_control_max_age_as_ttl(self):
        headers = {'ETag': '"xyz"', 'Cache-Control': 'max-age=120'}
        self.cache.store('https://example.com/api', headers)

        self.mock_db.set.assert_called_once_with(
            self.cache.make_key('etag', url='https://example.com/api'),
            '"xyz"',
            ex=timedelta(seconds=120),
        )

    def test_stores_both_etag_and_last_modified(self):
        headers = {
            'ETag': '"v1"',
            'Last-Modified': 'Mon, 01 Jan 2029 00:00:00 GMT',
        }
        self.cache.store('https://example.com/api', headers)

        self.assertEqual(self.mock_db.set.call_count, 2)

    def test_stores_nothing_when_no_etag_or_last_modified(self):
        self.cache.store('https://example.com/api', {'Content-Type': 'application/json'})

        self.mock_db.set.assert_not_called()


class HttpCacheDBGetConditionalHeadersTest(TestCase):
    def setUp(self):
        self.cache = HttpCacheDB('redis://localhost:6379/0')
        self.mock_db = MagicMock()
        self.cache._conn = self.mock_db

    def test_returns_if_none_match_when_etag_is_cached(self):
        self.mock_db.get.side_effect = lambda key: (
            b'"abc123"' if 'etag' in key else None
        )

        headers = self.cache.get_conditional_headers('https://example.com/api')

        self.assertEqual(headers.get('If-None-Match'), '"abc123"')
        self.assertNotIn('If-Modified-Since', headers)

    def test_returns_if_modified_since_when_last_modified_is_cached(self):
        self.mock_db.get.side_effect = lambda key: (
            b'Tue, 01 Jan 2030 00:00:00 GMT' if 'lm' in key else None
        )

        headers = self.cache.get_conditional_headers('https://example.com/api')

        self.assertEqual(headers.get('If-Modified-Since'), 'Tue, 01 Jan 2030 00:00:00 GMT')
        self.assertNotIn('If-None-Match', headers)

    def test_returns_both_headers_when_both_are_cached(self):
        etag_key = self.cache.make_key('etag', url='https://example.com/api')
        self.mock_db.get.side_effect = lambda key: (
            b'"v2"' if key == etag_key else b'Wed, 15 Mar 2028 12:00:00 GMT'
        )

        headers = self.cache.get_conditional_headers('https://example.com/api')

        self.assertIn('If-None-Match', headers)
        self.assertIn('If-Modified-Since', headers)

    def test_returns_empty_dict_when_nothing_is_cached(self):
        self.mock_db.get.return_value = None

        headers = self.cache.get_conditional_headers('https://example.com/api')

        self.assertEqual(headers, {})

    def test_decodes_bytes_etag_to_string(self):
        self.mock_db.get.side_effect = lambda key: (
            b'"bytes-etag"' if 'etag' in key else None
        )

        headers = self.cache.get_conditional_headers('https://example.com/api')

        self.assertIsInstance(headers['If-None-Match'], str)
        self.assertEqual(headers['If-None-Match'], '"bytes-etag"')
