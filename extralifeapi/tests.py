""" Tests for DonorDriveBase fetch and retry logic """
from json import JSONDecodeError
from unittest.mock import MagicMock, call, patch

from django.test import TestCase, override_settings

from .base import DonorDriveBase, FetchResponse, JSONError, RateLimitError


def _make_client(max_retries=2):
    """ Build a DonorDriveBase with the request sleeper disabled and a controlled retry count. """
    return DonorDriveBase(request_sleeper=None, max_retries=max_retries)


def _mock_response(status_code=200, json_data=None, headers=None, text='', raise_json=False):
    """ Build a mock requests.Response with the given attributes. """
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    response.text = text
    response.content = text.encode() if text else b''
    if raise_json:
        response.json.side_effect = JSONDecodeError('err', '', 0)
    else:
        response.json.return_value = json_data if json_data is not None else {}
    response.raise_for_status = MagicMock()
    return response


class GetRetrySleepTest(TestCase):
    def setUp(self):
        self.client = _make_client()

    @override_settings(EL_RETRY_AFTER_SECONDS=60)
    def test_uses_retry_after_header_when_present(self):
        response = _mock_response(headers={'Retry-After': '30'})
        self.assertEqual(self.client._get_retry_sleep(response), 30)

    @override_settings(EL_RETRY_AFTER_SECONDS=60)
    def test_falls_back_to_setting_when_header_absent(self):
        response = _mock_response(headers={})
        self.assertEqual(self.client._get_retry_sleep(response), 60)

    @override_settings(EL_RETRY_AFTER_SECONDS=60)
    def test_falls_back_to_setting_when_header_is_not_an_integer(self):
        # Some servers send a date string instead of seconds - we can't parse that, so use the default
        response = _mock_response(headers={'Retry-After': 'Wed, 01 Jan 2026 00:00:00 GMT'})
        self.assertEqual(self.client._get_retry_sleep(response), 60)


class ParseResponseJsonTest(TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_returns_parsed_json_on_success(self):
        response = _mock_response(json_data={'foo': 'bar'})
        result = self.client._parse_response_json('https://example.com', response, {})
        self.assertEqual(result, {'foo': 'bar'})

    def test_raises_json_error_on_decode_failure(self):
        response = _mock_response(raise_json=True, text='not json here')
        with self.assertRaises(JSONError):
            self.client._parse_response_json('https://example.com', response, {})

    def test_json_error_message_includes_truncated_response_text(self):
        long_text = 'x' * 200
        response = _mock_response(raise_json=True, text=long_text)
        with self.assertRaises(JSONError) as ctx:
            self.client._parse_response_json('https://example.com', response, {})
        # Only the first 100 characters of the body should appear in the error
        self.assertIn('x' * 100, str(ctx.exception))
        self.assertNotIn('x' * 101, str(ctx.exception))

    def test_json_error_handles_empty_response_text(self):
        response = _mock_response(raise_json=True, text='')
        with self.assertRaises(JSONError):
            self.client._parse_response_json('https://example.com', response, {})


class FetchJsonRetryTest(TestCase):
    def setUp(self):
        self.client = _make_client(max_retries=2)

    @patch('extralifeapi.base.time')
    def test_returns_data_on_success_without_retrying(self, mock_time):
        ok_response = _mock_response(json_data=[{'id': 1}])
        self.client.session.get = MagicMock(return_value=ok_response)

        result = self.client.fetch_json('https://example.com/api')

        self.assertIsInstance(result, FetchResponse)
        self.assertEqual(result.data, [{'id': 1}])
        self.client.session.get.assert_called_once()
        mock_time.sleep.assert_not_called()

    @override_settings(EL_RETRY_AFTER_SECONDS=60)
    @patch('extralifeapi.base.time')
    def test_retries_on_429_then_succeeds(self, mock_time):
        rate_limited = _mock_response(status_code=429, headers={'Retry-After': '5'})
        rate_limited.raise_for_status = MagicMock()
        ok_response = _mock_response(json_data={'ok': True})
        self.client.session.get = MagicMock(side_effect=[rate_limited, ok_response])

        result = self.client.fetch_json('https://example.com/api')

        self.assertEqual(result.data, {'ok': True})
        self.assertEqual(self.client.session.get.call_count, 2)
        mock_time.sleep.assert_called_once_with(5)

    @override_settings(EL_RETRY_AFTER_SECONDS=60)
    @patch('extralifeapi.base.time')
    def test_raises_rate_limit_error_when_retries_exhausted(self, mock_time):
        rate_limited = _mock_response(status_code=429, headers={'Retry-After': '5'})
        rate_limited.raise_for_status = MagicMock()
        # Return 429 on every attempt (max_retries=2 means 3 total attempts)
        self.client.session.get = MagicMock(return_value=rate_limited)

        with self.assertRaises(RateLimitError):
            self.client.fetch_json('https://example.com/api')

        self.assertEqual(self.client.session.get.call_count, 3)

    @override_settings(EL_RETRY_AFTER_SECONDS=60)
    @patch('extralifeapi.base.time')
    def test_sleeps_between_each_retry(self, mock_time):
        rate_limited = _mock_response(status_code=429, headers={'Retry-After': '10'})
        rate_limited.raise_for_status = MagicMock()
        ok_response = _mock_response(json_data={})
        # Two 429s then a success
        self.client.session.get = MagicMock(side_effect=[rate_limited, rate_limited, ok_response])

        self.client.fetch_json('https://example.com/api')

        self.assertEqual(mock_time.sleep.call_count, 2)
        mock_time.sleep.assert_has_calls([call(10), call(10)])

    @override_settings(EL_RETRY_AFTER_SECONDS=60)
    @patch('extralifeapi.base.time')
    def test_uses_default_sleep_when_retry_after_header_missing(self, mock_time):
        rate_limited = _mock_response(status_code=429, headers={})
        rate_limited.raise_for_status = MagicMock()
        ok_response = _mock_response(json_data={})
        self.client.session.get = MagicMock(side_effect=[rate_limited, ok_response])

        self.client.fetch_json('https://example.com/api')

        mock_time.sleep.assert_called_once_with(60)
