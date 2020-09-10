""" DonorDrive API Base Class """
from .log import root_logger
import requests
from collections import namedtuple
import re
from urllib.parse import urlparse
from json import JSONDecodeError

mod_logger = root_logger.getChild('base')
FetchResponse = namedtuple('FetchResponse', ['data', 'headers', 'urls'])


class FetchError(Exception):
    """ Top level problem with fetching a page """


class JSONError(FetchError):
    """ JSON issues """


class DonorDriveBase(object):
    DEFAULT_BASE_URL = 'https://www.extra-life.org/api/'
    RE_MATCH_LINK = re.compile(r'^\<(.*)\>;rel="(.*)"')

    def __init__(self, base_url=DEFAULT_BASE_URL, log_parent=mod_logger, request_sleeper=None):
        """
        :param base_url: Base EL API URL
        :param log_parent: Parent logger to base our logger off of
        :param request_sleeper: Function. Should take any kwargs. No positional args.
        Will get at a min url (string), data (query data), and parsed (urlparse obj).
        """
        self.base_url = base_url
        self.log_parent = log_parent
        self.log = self.log_parent.getChild(self.__class__.__name__)
        self.session = requests.Session()
        self.request_sleeper = request_sleeper

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

    def fetch_json(self, url, **kwargs):
        """ Fetch the given URL with the given data. Returns data structure from JSON or raises an error. """
        e = dict(url=url, data=kwargs)
        try:
            # Sleep before the call!
            self._do_sleep(url=url, data=kwargs)
            self.log.debug(f'Going to fetch {url}', extra=e)
            r = self.session.get(url, data=kwargs)
            e['result'] = r
            self.log.log(5, f'Got result from {url}', extra=e)
            r.raise_for_status()
            self.log.log(5, f"Status of {url} is ok", extra=e)
            try:
                j = r.json()
            except JSONDecodeError as er:
                e['raw'] = r.raw
                e['headers'] = r.headers
                e['rdata'] = r.content
                e['text'] = r.text
                rd = ''
                if r.text:
                    rd = r.text[:100]
                self.log.exception(f"Failed to decode JSON with {er} for {url} | Data: {rd}", extra=e)
                raise JSONError(f"Failed to decode JSON with {er} for {url} | Data: {rd}")
            e['data_len'] = len(j)
            e['data'] = j
            self.log.debug(f"Got JSON data from {url}", extra=e)
            return FetchResponse(j, r.headers, self._parse_link_header(r.headers.get('Link', None)))
        finally:
            self.log.log(5, f"Done fetching {url}", extra=e)

    def fetch(self, sub_url, **kwargs):
        """ Fetch all records """
        url = "%s/%s" % (self.base_url, sub_url)
        e = dict(url=url, data=kwargs)

        fresp = self.fetch_json(url=url, **kwargs)
        for row in fresp.data:
            yield row

        while 'next' in fresp.urls:
            fresp = self.fetch_json(url=fresp.urls['next'])
            for row in fresp.data:
                yield row
