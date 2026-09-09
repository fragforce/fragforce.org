""" Tests for DonorDriveBase fetch and retry logic """
from json import JSONDecodeError
from unittest.mock import MagicMock, call, patch

import requests.exceptions
from django.test import TestCase, override_settings

from .base import (
    DonorDriveBase,
    FetchResponse,
    JSONError,
    NetworkError,
    NotModifiedResponse,
    RateLimitError,
    ServerError,
)
from .donors import Donations
from .participants import Participants
from .teams import Teams


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


def _make_client_with_server_retries(server_max_retries=2):
    """ Build a DonorDriveBase with server_max_retries set and rate-limit retries disabled. """
    return DonorDriveBase(request_sleeper=None, max_retries=0, server_max_retries=server_max_retries)


class FetchJsonServerErrorRetryTest(TestCase):
    def setUp(self):
        self.client = _make_client_with_server_retries(server_max_retries=2)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=5)
    @patch('extralifeapi.base.time')
    def test_retries_on_500_then_succeeds(self, mock_time):
        server_error = _mock_response(status_code=500)
        ok_response = _mock_response(json_data={'ok': True})
        self.client.session.get = MagicMock(side_effect=[server_error, ok_response])

        result = self.client.fetch_json('https://example.com/api')

        self.assertEqual(result.data, {'ok': True})
        self.assertEqual(self.client.session.get.call_count, 2)
        mock_time.sleep.assert_called_once_with(5)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=5)
    @patch('extralifeapi.base.time')
    def test_retries_on_503_then_succeeds(self, mock_time):
        server_error = _mock_response(status_code=503)
        ok_response = _mock_response(json_data={'ok': True})
        self.client.session.get = MagicMock(side_effect=[server_error, ok_response])

        result = self.client.fetch_json('https://example.com/api')

        self.assertEqual(result.data, {'ok': True})
        self.assertEqual(self.client.session.get.call_count, 2)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=5)
    @patch('extralifeapi.base.time')
    def test_raises_server_error_when_retries_exhausted(self, mock_time):
        server_error = _mock_response(status_code=500)
        # Return 500 on every attempt (server_max_retries=2 means 3 total attempts)
        self.client.session.get = MagicMock(return_value=server_error)

        with self.assertRaises(ServerError):
            self.client.fetch_json('https://example.com/api')

        self.assertEqual(self.client.session.get.call_count, 3)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=7)
    @patch('extralifeapi.base.time')
    def test_sleeps_el_server_retry_after_seconds_between_5xx_retries(self, mock_time):
        server_error = _mock_response(status_code=500)
        ok_response = _mock_response(json_data={})
        self.client.session.get = MagicMock(side_effect=[server_error, server_error, ok_response])

        self.client.fetch_json('https://example.com/api')

        self.assertEqual(mock_time.sleep.call_count, 2)
        mock_time.sleep.assert_has_calls([call(7), call(7)])


class FetchJsonNetworkErrorRetryTest(TestCase):
    def setUp(self):
        self.client = _make_client_with_server_retries(server_max_retries=2)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=5)
    @patch('extralifeapi.base.time')
    def test_retries_on_connection_error_then_succeeds(self, mock_time):
        ok_response = _mock_response(json_data={'ok': True})
        self.client.session.get = MagicMock(
            side_effect=[requests.exceptions.ConnectionError('refused'), ok_response]
        )

        result = self.client.fetch_json('https://example.com/api')

        self.assertEqual(result.data, {'ok': True})
        self.assertEqual(self.client.session.get.call_count, 2)
        mock_time.sleep.assert_called_once_with(5)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=5)
    @patch('extralifeapi.base.time')
    def test_retries_on_timeout_then_succeeds(self, mock_time):
        ok_response = _mock_response(json_data={'ok': True})
        self.client.session.get = MagicMock(
            side_effect=[requests.exceptions.Timeout('timed out'), ok_response]
        )

        result = self.client.fetch_json('https://example.com/api')

        self.assertEqual(result.data, {'ok': True})
        self.assertEqual(self.client.session.get.call_count, 2)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=5)
    @patch('extralifeapi.base.time')
    def test_raises_network_error_when_retries_exhausted(self, mock_time):
        self.client.session.get = MagicMock(
            side_effect=requests.exceptions.ConnectionError('refused')
        )

        with self.assertRaises(NetworkError):
            self.client.fetch_json('https://example.com/api')

        self.assertEqual(self.client.session.get.call_count, 3)

    @override_settings(EL_SERVER_RETRY_AFTER_SECONDS=5)
    @patch('extralifeapi.base.time')
    def test_raises_network_error_on_repeated_timeouts(self, mock_time):
        self.client.session.get = MagicMock(
            side_effect=requests.exceptions.Timeout('timed out')
        )

        with self.assertRaises(NetworkError):
            self.client.fetch_json('https://example.com/api')

        self.assertEqual(self.client.session.get.call_count, 3)


class FetchJsonConditionalGetTest(TestCase):
    def setUp(self):
        self.mock_cache = MagicMock()
        self.client = DonorDriveBase(request_sleeper=None, max_retries=0, http_cache=self.mock_cache)

    @patch('extralifeapi.base.time')
    def test_sends_if_none_match_header_when_etag_is_cached(self, mock_time):
        # Cache returns an ETag for the URL
        self.mock_cache.get_conditional_headers.return_value = {'If-None-Match': '"abc123"'}
        ok_response = _mock_response(json_data={'id': 1})
        self.client.session.get = MagicMock(return_value=ok_response)

        self.client.fetch_json('https://example.com/api')

        self.client.session.get.assert_called_once_with(
            'https://example.com/api',
            data={},
            headers={'If-None-Match': '"abc123"'},
        )

    @patch('extralifeapi.base.time')
    def test_returns_not_modified_response_on_304(self, mock_time):
        self.mock_cache.get_conditional_headers.return_value = {}
        not_modified = _mock_response(status_code=304)
        self.client.session.get = MagicMock(return_value=not_modified)

        result = self.client.fetch_json('https://example.com/api')

        self.assertIsInstance(result, NotModifiedResponse)

    @patch('extralifeapi.base.time')
    def test_stores_response_headers_in_cache_after_200(self, mock_time):
        self.mock_cache.get_conditional_headers.return_value = {}
        ok_response = _mock_response(
            json_data={'id': 1},
            headers={'ETag': '"newetag"', 'Cache-Control': 'max-age=60'},
        )
        self.client.session.get = MagicMock(return_value=ok_response)

        self.client.fetch_json('https://example.com/api')

        self.mock_cache.store.assert_called_once_with(
            'https://example.com/api',
            ok_response.headers,
        )

    @patch('extralifeapi.base.time')
    def test_does_not_store_headers_on_304(self, mock_time):
        self.mock_cache.get_conditional_headers.return_value = {}
        not_modified = _mock_response(status_code=304)
        self.client.session.get = MagicMock(return_value=not_modified)

        self.client.fetch_json('https://example.com/api')

        self.mock_cache.store.assert_not_called()

    @patch('extralifeapi.base.time')
    def test_no_conditional_headers_sent_when_cache_is_none(self, mock_time):
        # Client with no http_cache should not send conditional headers
        client = DonorDriveBase(request_sleeper=None, max_retries=0, http_cache=None)
        ok_response = _mock_response(json_data={})
        client.session.get = MagicMock(return_value=ok_response)

        client.fetch_json('https://example.com/api')

        # Called with empty headers dict since there's no cache
        client.session.get.assert_called_once_with(
            'https://example.com/api',
            data={},
            headers={},
        )


class FetchConditionalGetTest(TestCase):
    def setUp(self):
        self.mock_cache = MagicMock()
        self.client = DonorDriveBase(
            base_url='https://example.com/api/',
            request_sleeper=None,
            max_retries=0,
            http_cache=self.mock_cache,
        )

    @patch('extralifeapi.base.time')
    def test_yields_nothing_on_304(self, mock_time):
        # When fetch_json returns NotModifiedResponse, fetch should yield nothing
        self.mock_cache.get_conditional_headers.return_value = {}
        not_modified = _mock_response(status_code=304)
        self.client.session.get = MagicMock(return_value=not_modified)

        results = list(self.client.fetch('teams/1234'))

        self.assertEqual(results, [])

    @patch('extralifeapi.base.time')
    def test_yields_items_on_200(self, mock_time):
        self.mock_cache.get_conditional_headers.return_value = {}
        ok_response = _mock_response(json_data=[{'teamID': 1}, {'teamID': 2}])
        self.client.session.get = MagicMock(return_value=ok_response)

        results = list(self.client.fetch('teams'))

        self.assertEqual(len(results), 2)


class ParseLinkHeaderTest(TestCase):
    def test_returns_empty_dict_for_none(self):
        self.assertEqual(DonorDriveBase._parse_link_header(None), {})

    def test_parses_single_next_relation(self):
        link = '<https://www.extra-life.org/api/teams?offset=100>;rel="next"'
        result = DonorDriveBase._parse_link_header(link)
        self.assertEqual(result, {'next': 'https://www.extra-life.org/api/teams?offset=100'})

    def test_parses_multiple_relations(self):
        link = '<https://www.extra-life.org/api/teams?offset=100>;rel="next",<https://www.extra-life.org/api/teams?offset=0>;rel="first"'
        result = DonorDriveBase._parse_link_header(link)
        self.assertEqual(result['next'], 'https://www.extra-life.org/api/teams?offset=100')
        self.assertEqual(result['first'], 'https://www.extra-life.org/api/teams?offset=0')

    def test_relation_names_are_lowercased(self):
        link = '<https://www.extra-life.org/api/teams?offset=100>;rel="Next"'
        result = DonorDriveBase._parse_link_header(link)
        self.assertIn('next', result)

    def test_returns_empty_dict_for_malformed_entry(self):
        # Standard RFC 5988 uses spaces around the semicolon - the regex does not support this
        link = '<https://www.extra-life.org/api/teams?offset=100>; rel="next"'
        result = DonorDriveBase._parse_link_header(link)
        self.assertEqual(result, {})


class FetchJsonResponseHeadersTest(TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_returns_response_headers_in_fetch_response(self):
        ok_response = _mock_response(json_data={}, headers={'ETag': '"abc123"', 'API-Version': '1.4'})
        self.client.session.get = MagicMock(return_value=ok_response)

        result = self.client.fetch_json('https://example.com/api')

        self.assertEqual(result.headers.get('ETag'), '"abc123"')
        self.assertEqual(result.headers.get('API-Version'), '1.4')

    def test_parses_link_header_into_urls(self):
        ok_response = _mock_response(
            json_data=[],
            headers={'Link': '<https://www.extra-life.org/api/teams?offset=100>;rel="next"'}
        )
        self.client.session.get = MagicMock(return_value=ok_response)

        result = self.client.fetch_json('https://example.com/api')

        self.assertIn('next', result.urls)
        self.assertEqual(result.urls['next'], 'https://www.extra-life.org/api/teams?offset=100')

    def test_urls_is_empty_dict_when_no_link_header(self):
        ok_response = _mock_response(json_data={}, headers={})
        self.client.session.get = MagicMock(return_value=ok_response)

        result = self.client.fetch_json('https://example.com/api')

        self.assertEqual(result.urls, {})


class FetchPaginationTest(TestCase):
    def setUp(self):
        self.client = _make_client()

    def test_yields_all_items_from_a_list_response(self):
        ok_response = _mock_response(json_data=[{'id': 1}, {'id': 2}])
        self.client.session.get = MagicMock(return_value=ok_response)

        results = list(self.client.fetch('teams'))

        self.assertEqual(results, [{'id': 1}, {'id': 2}])

    def test_wraps_single_object_response_in_a_list(self):
        # /api/teams/{teamID} returns an object, not an array - fetch should still yield it
        ok_response = _mock_response(json_data={'teamID': 42, 'name': 'Test Team'})
        self.client.session.get = MagicMock(return_value=ok_response)

        results = list(self.client.fetch('teams/42'))

        self.assertEqual(results, [{'teamID': 42, 'name': 'Test Team'}])

    def test_follows_next_link_header_to_fetch_subsequent_pages(self):
        page1 = _mock_response(
            json_data=[{'id': 1}],
            headers={'Link': '<https://www.extra-life.org/api/teams?offset=1>;rel="next"'}
        )
        page2 = _mock_response(json_data=[{'id': 2}])
        self.client.session.get = MagicMock(side_effect=[page1, page2])

        results = list(self.client.fetch('teams'))

        self.assertEqual(results, [{'id': 1}, {'id': 2}])
        self.assertEqual(self.client.session.get.call_count, 2)

    def test_builds_correct_url_from_base_url_and_sub_url(self):
        ok_response = _mock_response(json_data=[])
        self.client.session.get = MagicMock(return_value=ok_response)

        list(self.client.fetch('teams/42'))

        called_url = self.client.session.get.call_args[0][0]
        self.assertEqual(called_url, 'https://www.extra-life.org/api/teams/42')


class DoSleepTest(TestCase):
    def test_returns_none_when_no_sleeper_configured(self):
        client = _make_client()
        result = client._do_sleep('https://example.com/api', {})
        self.assertIsNone(result)

    def test_calls_sleeper_with_url_data_and_parsed_url(self):
        mock_sleeper = MagicMock(return_value='slept')
        client = DonorDriveBase(request_sleeper=mock_sleeper, max_retries=0)

        result = client._do_sleep('https://example.com/api', {'key': 'val'})

        mock_sleeper.assert_called_once()
        kwargs = mock_sleeper.call_args.kwargs
        self.assertEqual(kwargs['url'], 'https://example.com/api')
        self.assertEqual(kwargs['data'], {'key': 'val'})
        self.assertEqual(kwargs['parsed'].netloc, 'example.com')
        self.assertEqual(result, 'slept')


class TeamMappingTest(TestCase):
    def test_maps_all_api_fields_to_namedtuple(self):
        data = {
            'teamID': 8775,
            'name': 'The Bonhams',
            'avatarImageURL': 'https://example.com/avatar.gif',
            'createdDateUTC': '2019-11-02T15:02:38.93+0000',
            'eventID': 508,
            'eventName': 'Test Participant Event',
            'fundraisingGoal': 20000.0,
            'numDonations': 97,
            'sumDonations': 9349.5,
        }
        team = Teams._team_to_team(data)

        self.assertEqual(team.teamID, 8775)
        self.assertEqual(team.name, 'The Bonhams')
        self.assertEqual(team.eventID, 508)
        self.assertEqual(team.sumDonations, 9349.5)
        self.assertEqual(team.numDonations, 97)
        self.assertIs(team.raw, data)

    def test_missing_optional_fields_default_to_none(self):
        # Only teamID is provided - all other fields should be None
        team = Teams._team_to_team({'teamID': 1})

        self.assertEqual(team.teamID, 1)
        self.assertIsNone(team.name)
        self.assertIsNone(team.fundraisingGoal)
        self.assertIsNone(team.eventID)

    def test_sub_team_by_tid_builds_correct_url(self):
        client = Teams(max_retries=0)
        self.assertEqual(client.sub_team_by_tid(8775), 'teams/8775')

    def test_sub_team_by_eid_builds_correct_url(self):
        client = Teams(max_retries=0)
        self.assertEqual(client.sub_team_by_eid(508), 'events/508/teams')


class ParticipantMappingTest(TestCase):
    def test_maps_all_api_fields_to_namedtuple(self):
        data = {
            'participantID': 19265,
            'displayName': 'Liam Bonham',
            'fundraisingGoal': 8000.0,
            'eventID': 508,
            'eventName': 'Test Participant Event',
            'teamID': 8775,
            'teamName': 'The Bonhams',
            'isTeamCaptain': True,
            'sumDonations': 4661.0,
            'numDonations': 51,
            'avatarImageURL': 'https://example.com/avatar.gif',
            'createdDateUTC': '2019-11-02T15:02:38.93+0000',
        }
        p = Participants._p_to_p(data)

        self.assertEqual(p.participantID, 19265)
        self.assertEqual(p.displayName, 'Liam Bonham')
        self.assertTrue(p.isTeamCaptain)
        self.assertEqual(p.teamID, 8775)
        self.assertIs(p.raw, data)

    def test_missing_optional_fields_default_to_none(self):
        # teamID and teamName are only present for team participants per the API docs
        p = Participants._p_to_p({'participantID': 1})

        self.assertIsNone(p.teamID)
        self.assertIsNone(p.teamName)
        self.assertIsNone(p.isTeamCaptain)

    def test_sub_url_methods_build_correct_paths(self):
        client = Participants(max_retries=0)
        self.assertEqual(client.sub_by_pid(19265), 'participants/19265')
        self.assertEqual(client.sub_by_tid(8775), 'teams/8775/participants')
        self.assertEqual(client.sub_by_eid(508), 'events/508/participants')


class ParticipantFetchTest(TestCase):
    def setUp(self):
        self.client = Participants(request_sleeper=None, max_retries=0)

    @patch('extralifeapi.base.time')
    def test_participant_returns_namedtuple_for_single_object_response(self, mock_time):
        # /participants/{id} returns a single object, not an array - participant() must unwrap it correctly
        data = {
            'participantID': 19265,
            'displayName': 'Liam Bonham',
            'fundraisingGoal': 8000.0,
            'eventID': 508,
            'teamID': 8775,
            'isTeamCaptain': True,
            'sumDonations': 4661.0,
            'numDonations': 51,
        }
        response = _mock_response(json_data=data)
        self.client.session.get = MagicMock(return_value=response)

        result = self.client.participant(19265)

        self.assertEqual(result.participantID, 19265)
        self.assertEqual(result.displayName, 'Liam Bonham')
        self.assertEqual(result.teamID, 8775)

    @patch('extralifeapi.base.time')
    def test_participant_accepts_vanity_slug(self, mock_time):
        data = {'participantID': 19265, 'displayName': 'Liam Bonham', 'eventID': 508,
                'teamID': 8775, 'fundraisingGoal': 8000.0, 'sumDonations': 0.0, 'numDonations': 0}
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=data))

        result = self.client.participant('liambonham2024')

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('participants/liambonham2024', called_url)
        self.assertEqual(result.participantID, 19265)


class DonationMappingTest(TestCase):
    def test_maps_all_api_fields_to_namedtuple(self):
        data = {
            'donationID': 'DF4E676D0828A8D5',
            'amount': 10.0,
            'displayName': 'Friendly Donor',
            'donorID': 'EB8610A3FC435D58',
            'participantID': 4024,
            'teamID': 5074,
            'message': 'Great job!',
            'createdDateUTC': '2019-10-30T18:01:18.513+0000',
            'avatarImageURL': 'https://example.com/avatar.gif',
        }
        d = Donations._d_to_d(data)

        self.assertEqual(d.donationID, 'DF4E676D0828A8D5')
        self.assertEqual(d.amount, 10.0)
        self.assertEqual(d.displayName, 'Friendly Donor')
        self.assertEqual(d.message, 'Great job!')
        self.assertIs(d.raw, data)

    def test_missing_optional_fields_default_to_none(self):
        # displayName and message are not guaranteed - privacy settings may hide them per the API docs
        d = Donations._d_to_d({'donationID': 'ABC123', 'amount': 5.0})

        self.assertIsNone(d.message)
        self.assertIsNone(d.displayName)
        self.assertIsNone(d.participantID)

    def test_sub_url_methods_build_correct_paths(self):
        client = Donations(max_retries=0)
        self.assertEqual(client.sub_by_pid(4024), 'participants/4024/donations')
        self.assertEqual(client.sub_by_tid(5074), 'teams/5074/donations')


# Shared fixture data matching the DonorDrive API docs examples

_TEAM_DATA = {
    'teamID': 8775,
    'name': 'The Bonhams',
    'avatarImageURL': 'https://static.donordrive.com/clients/testdrive/img/avatar-team-default.gif',
    'createdDateUTC': '2019-11-02T15:02:38.93+0000',
    'eventID': 508,
    'eventName': 'Test Participant Event',
    'fundraisingGoal': 20000.0,
    'numDonations': 97,
    'sumDonations': 9349.5,
}

_PARTICIPANT_DATA = {
    'participantID': 19265,
    'displayName': 'Liam Bonham',
    'fundraisingGoal': 8000.0,
    'eventID': 508,
    'eventName': 'Test Participant Event',
    'teamID': 8775,
    'teamName': 'The Bonhams',
    'isTeamCaptain': True,
    'sumDonations': 4661.0,
    'numDonations': 51,
    'avatarImageURL': 'https://static.donordrive.com/clients/testdrive/img/avatar-constituent-default.gif',
    'createdDateUTC': '2019-11-02T15:02:38.93+0000',
}

_DONATION_DATA = {
    'donationID': 'DF4E676D0828A8D5',
    'amount': 10.0,
    'displayName': 'Friendly Donor',
    'donorID': 'EB8610A3FC435D58',
    'participantID': 4024,
    'teamID': 5074,
    'message': 'Great job!',
    'createdDateUTC': '2019-10-30T18:01:18.513+0000',
    'avatarImageURL': 'https://static.donordrive.com/clients/testdrive/img/avatar-constituent-default.gif',
}


class TeamsFetchTest(TestCase):
    def setUp(self):
        self.client = Teams(request_sleeper=None, max_retries=0)

    @patch('extralifeapi.base.time')
    def test_team_returns_single_team_namedtuple(self, mock_time):
        # /teams/{teamID} returns a single object - team() must unwrap it and map to namedtuple
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=_TEAM_DATA))

        result = self.client.team(8775)

        self.assertEqual(result.teamID, 8775)
        self.assertEqual(result.name, 'The Bonhams')
        self.assertEqual(result.eventID, 508)
        self.assertEqual(result.sumDonations, 9349.5)

    @patch('extralifeapi.base.time')
    def test_team_requests_correct_url(self, mock_time):
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=_TEAM_DATA))

        self.client.team(8775)

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('teams/8775', called_url)

    @patch('extralifeapi.base.time')
    def test_team_accepts_vanity_slug(self, mock_time):
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=_TEAM_DATA))

        result = self.client.team('fragforce-dcm')

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('teams/fragforce-dcm', called_url)
        self.assertEqual(result.teamID, 8775)

    @patch('extralifeapi.base.time')
    def test_teams_yields_team_namedtuples(self, mock_time):
        # /teams returns an array - teams() should yield one namedtuple per item
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_TEAM_DATA, {**_TEAM_DATA, 'teamID': 9000}])
        )

        results = list(self.client.teams())

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].teamID, 8775)
        self.assertEqual(results[1].teamID, 9000)

    @patch('extralifeapi.base.time')
    def test_event_teams_requests_correct_url(self, mock_time):
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=[_TEAM_DATA]))

        list(self.client.event_teams(508))

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('events/508/teams', called_url)

    @patch('extralifeapi.base.time')
    def test_event_teams_yields_team_namedtuples(self, mock_time):
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=[_TEAM_DATA]))

        results = list(self.client.event_teams(508))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].teamID, 8775)
        self.assertEqual(results[0].name, 'The Bonhams')


class ParticipantsFetchTest(TestCase):
    def setUp(self):
        self.client = Participants(request_sleeper=None, max_retries=0)

    @patch('extralifeapi.base.time')
    def test_participants_for_team_yields_participant_namedtuples(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_PARTICIPANT_DATA])
        )

        results = list(self.client.participants_for_team(8775))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].participantID, 19265)
        self.assertEqual(results[0].displayName, 'Liam Bonham')

    @patch('extralifeapi.base.time')
    def test_participants_for_team_requests_correct_url(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_PARTICIPANT_DATA])
        )

        list(self.client.participants_for_team(8775))

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('teams/8775/participants', called_url)

    @patch('extralifeapi.base.time')
    def test_participants_for_event_requests_correct_url(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_PARTICIPANT_DATA])
        )

        list(self.client.participants_for_event(508))

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('events/508/participants', called_url)

    @patch('extralifeapi.base.time')
    def test_participants_for_event_yields_participant_namedtuples(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_PARTICIPANT_DATA])
        )

        results = list(self.client.participants_for_event(508))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].participantID, 19265)
        self.assertTrue(results[0].isTeamCaptain)

    @patch('extralifeapi.base.time')
    def test_participants_for_team_yields_empty_on_empty_response(self, mock_time):
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=[]))

        results = list(self.client.participants_for_team(8775))

        self.assertEqual(results, [])


class DonationsFetchTest(TestCase):
    def setUp(self):
        self.client = Donations(request_sleeper=None, max_retries=0)

    @patch('extralifeapi.base.time')
    def test_donations_for_team_yields_donation_namedtuples(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_DONATION_DATA])
        )

        results = list(self.client.donations_for_team(5074))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].donationID, 'DF4E676D0828A8D5')
        self.assertEqual(results[0].amount, 10.0)
        self.assertEqual(results[0].displayName, 'Friendly Donor')

    @patch('extralifeapi.base.time')
    def test_donations_for_team_requests_correct_url(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_DONATION_DATA])
        )

        list(self.client.donations_for_team(5074))

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('teams/5074/donations', called_url)

    @patch('extralifeapi.base.time')
    def test_donations_for_participants_yields_donation_namedtuples(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_DONATION_DATA])
        )

        results = list(self.client.donations_for_participants(4024))

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].donationID, 'DF4E676D0828A8D5')
        self.assertEqual(results[0].participantID, 4024)

    @patch('extralifeapi.base.time')
    def test_donations_for_participants_requests_correct_url(self, mock_time):
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_DONATION_DATA])
        )

        list(self.client.donations_for_participants(4024))

        called_url = self.client.session.get.call_args[0][0]
        self.assertIn('participants/4024/donations', called_url)

    @patch('extralifeapi.base.time')
    def test_donations_for_team_yields_empty_on_empty_response(self, mock_time):
        self.client.session.get = MagicMock(return_value=_mock_response(json_data=[]))

        results = list(self.client.donations_for_team(5074))

        self.assertEqual(results, [])

    @patch('extralifeapi.base.time')
    def test_donations_for_team_yields_multiple_donations(self, mock_time):
        second = {**_DONATION_DATA, 'donationID': 'AABBCCDD', 'amount': 25.0}
        self.client.session.get = MagicMock(
            return_value=_mock_response(json_data=[_DONATION_DATA, second])
        )

        results = list(self.client.donations_for_team(5074))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[1].donationID, 'AABBCCDD')
        self.assertEqual(results[1].amount, 25.0)
