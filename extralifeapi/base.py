""" DonorDrive API Base Class """
import re
import time
from collections import namedtuple
from json import JSONDecodeError
from urllib.parse import urlparse

import requests
import requests.exceptions
from django.conf import settings

from .log import root_logger

mod_logger = root_logger.getChild('base')
FetchResponse = namedtuple('FetchResponse', ['data', 'headers', 'urls'])


class FetchError(Exception):
    """ Top level problem with fetching a page """


class JSONError(FetchError):
    """ JSON issues """


class RateLimitError(FetchError):
    """ API rate limit hit and retries exhausted """


class ServerError(FetchError):
    """ Server-side 5xx error with retries exhausted """


class NetworkError(FetchError):
    """ Network-level error (connection refused, timeout) with retries exhausted """


class NotModifiedResponse:
    """ Sentinel returned by fetch_json when the API responds 304 Not Modified """


class DonorDriveBase(object):
    DEFAULT_BASE_URL = 'https://www.extra-life.org/api/'
    RE_MATCH_LINK = re.compile(r'^\<([^>]*)\>;rel="([^"]*)"')

    def __init__(self, base_url=DEFAULT_BASE_URL, log_parent=mod_logger, request_sleeper=None,
                 max_retries=None, server_max_retries=None, http_cache=None):
        """
        :param base_url: Base EL API URL
        :param log_parent: Parent logger to base our logger off of
        :param request_sleeper: Function. Should take any kwargs. No positional args.
        Will get at a min url (string), data (query data), and parsed (urlparse obj).
        :param max_retries: Number of times to retry on a 429 rate limit response.
        :param server_max_retries: Number of times to retry on a 5xx or network error.
        :param http_cache: HttpCacheDB instance for ETag/Last-Modified conditional GET support.
        """
        self.base_url = base_url
        self.log_parent = log_parent
        self.log = self.log_parent.getChild(self.__class__.__name__)
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "fragforce.org"})
        self.request_sleeper = request_sleeper
        self.max_retries = max_retries if max_retries is not None else settings.EL_MAX_RETRIES
        self.server_max_retries = (
            server_max_retries if server_max_retries is not None
            else settings.EL_SERVER_MAX_RETRIES
        )
        self.http_cache = http_cache

    def _do_sleep(self, url, data):
        """ Sleep or do whatever between requests to ensure they don't happen too often """
        parsed = urlparse(url)
        e = dict(url=url, data=data, f=self.request_sleeper, parsed=parsed)
        try:
            self.log.log(5, "Sleeping if needed", extra=e)
            if self.request_sleeper is None:
                self.log.log(5, "No sleep function defined", extra=e)
                return None
            else:
                self.log.log(5, "Sleeping per function", extra=e)
                return self.request_sleeper(url=url, data=data, parsed=parsed)
        finally:
            self.log.log(5, "Done with sleep", extra=e)

    @classmethod
    def _parse_link_header(cls, link):
        if link is None:
            return {}
        n = {}
        for a in link.split(','):
            match = cls.RE_MATCH_LINK.match(a)
            if match:
                r = match.groups()
                n[r[1].lower()] = r[0]
            else:
                return {}
        return n

    def _get_retry_sleep(self, response):
        """ Return how many seconds to sleep after a 429, using the Retry-After header or the configured default. """
        retry_after = response.headers.get('Retry-After', None)
        try:
            return int(retry_after) if retry_after is not None else settings.EL_RETRY_AFTER_SECONDS
        except ValueError:
            return settings.EL_RETRY_AFTER_SECONDS

    def _parse_response_json(self, url, response, e):
        """ Parse JSON from a response, or raise JSONError with context on failure. """
        try:
            return response.json()
        except JSONDecodeError as er:
            e['raw'] = response.raw
            e['headers'] = response.headers
            e['rdata'] = response.content
            e['text'] = response.text
            rd = response.text[:100] if response.text else ''
            self.log.exception(f"Failed to decode JSON with {er} for {url} | Data: {rd}", extra=e)
            raise JSONError(f"Failed to decode JSON with {er} for {url} | Data: {rd}")

    def _fetch_attempt(self, url, attempt, req_headers, kwargs, e):
        """ Make one fetch attempt. Returns FetchResponse or NotModifiedResponse on success, None to retry. """
        self._do_sleep(url=url, data=kwargs)
        self.log.debug(f'Going to fetch {url}', extra=e)
        try:
            r = self.session.get(url, data=kwargs, headers=req_headers)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as err:
            if attempt >= self.server_max_retries:
                raise NetworkError(f"Network error fetching {url} after {self.server_max_retries} retries: {err}")
            self.log.warning(
                f"Network error fetching {url}, retrying (attempt {attempt + 1}/{self.server_max_retries}): {err}",
                extra=e
                )
            time.sleep(settings.EL_SERVER_RETRY_AFTER_SECONDS)
            return None

        e['result'] = r
        self.log.log(5, f'Got result from {url}', extra=e)

        if r.status_code == 304:
            self.log.debug(f"Not modified: {url}", extra=e)
            return NotModifiedResponse()

        if r.status_code == 429:
            if attempt >= self.max_retries:
                raise RateLimitError(f"Rate limit hit for {url} and retries exhausted")
            sleep_secs = self._get_retry_sleep(r)
            self.log.warning(
                f"Rate limited by {url}, sleeping {sleep_secs}s (attempt {attempt + 1}/{self.max_retries})",
                extra=e
                )
            time.sleep(sleep_secs)
            return None

        if r.status_code >= 500:
            if attempt >= self.server_max_retries:
                raise ServerError(f"Server error {r.status_code} from {url} and retries exhausted")
            self.log.warning(
                f"Server error {r.status_code} from {url}, retrying (attempt {attempt + 1}/{self.server_max_retries})",
                extra=e
                )
            time.sleep(settings.EL_SERVER_RETRY_AFTER_SECONDS)
            return None

        r.raise_for_status()
        self.log.log(5, f"Status of {url} is ok", extra=e)

        if self.http_cache:
            self.http_cache.store(url, r.headers)

        j = self._parse_response_json(url, r, e)
        e['data_len'] = len(j)
        e['data'] = j
        self.log.debug(f"Got JSON data from {url}", extra=e)
        return FetchResponse(j, r.headers, self._parse_link_header(r.headers.get('Link', None)))

    def fetch_json(self, url, **kwargs):
        """ Fetch the given URL with the given data. Returns data structure from JSON or raises an error.
        Returns NotModifiedResponse if the API responds 304 Not Modified. """
        e = dict(url=url, data=kwargs)
        try:
            req_headers = {}
            if self.http_cache:
                req_headers.update(self.http_cache.get_conditional_headers(url))

            for attempt in range(max(self.max_retries, self.server_max_retries) + 1):
                result = self._fetch_attempt(url, attempt, req_headers, kwargs, e)
                if result is not None:
                    return result
        finally:
            self.log.log(5, f"Done fetching {url}", extra=e)

    def fetch(self, sub_url, **kwargs):
        """ Fetch all records. Yields nothing if the API returns 304 Not Modified. """
        url = "%s/%s" % (self.base_url.rstrip('/'), sub_url)

        fresp = self.fetch_json(url=url, **kwargs)
        if isinstance(fresp, NotModifiedResponse):
            return

        if isinstance(fresp.data, list):
            for row in fresp.data:
                yield row
        else:
            yield fresp.data

        while 'next' in fresp.urls:
            fresp = self.fetch_json(url=fresp.urls['next'])
            if isinstance(fresp, NotModifiedResponse):
                return
            for row in fresp.data:
                yield row
