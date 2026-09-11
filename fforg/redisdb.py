""" Redis based caching and data storage """
import hashlib
import time
from datetime import timedelta

import redis
from django.conf import settings


class RedisDB(object):
    def __init__(self, rurl):
        self.url = rurl
        self._conn = None

    @property
    def db(self):
        # TODO: Add a ping in here
        if self._conn is None:
            self._conn = redis.StrictRedis.from_url(self.url)
        return self._conn

    def make_key(self, name, *args, **kwargs):
        kwsort = list(kwargs.items())
        kwsort.sort(key=lambda x: x[0])
        arg_list = [name, ] + list(args) + [f"{k}={v}" for k, v in kwsort]
        return '_'.join(arg_list)

    def make_key_secure(self, name, *args, **kwargs):
        secret = settings.SECRET_KEY
        shahash = hashlib.new('sha512')
        shahash.update(secret)
        shahash.update(self.make_key(name=name, *args, **kwargs))
        return str(shahash)


class TimersDB(RedisDB):
    def time_until(self, key, delta=timedelta(seconds=1), now=None):
        if now is None:
            now = time.time()
        """ The amount of time between calls. Zero if not called before.
        Doesn't really do concurrency but it's "good enough" for now.
        """
        r = self.db.get(key)
        if r is None:
            self.db.set(key, str(now), ex=delta)
            return timedelta(seconds=0)
        r = float(r)
        expected = r + delta.total_seconds()
        # Seconds until expected
        diff = expected - now
        if diff <= 0:
            self.db.set(key, str(now), ex=delta)
            return timedelta(seconds=0)
        return timedelta(seconds=diff)

    def reset(self, key, delta):
        """ Mark a timer as triggered right now, gating subsequent callers for delta. """
        now = time.time()
        self.db.set(key, str(now), ex=delta)


class HttpCacheDB(RedisDB):
    DEFAULT_TTL = timedelta(hours=1)

    def store(self, url, headers):
        """ Store ETag and Last-Modified from response headers, using Cache-Control max-age as TTL. """
        ttl = self._parse_max_age(headers.get('Cache-Control', '')) or self.DEFAULT_TTL
        etag = headers.get('ETag', None)
        if etag:
            self.db.set(self.make_key('etag', url=url), etag, ex=ttl)
        last_modified = headers.get('Last-Modified', None)
        if last_modified:
            self.db.set(self.make_key('lm', url=url), last_modified, ex=ttl)

    def get_conditional_headers(self, url):
        """ Return If-None-Match and/or If-Modified-Since headers for a URL if we have cached values. """
        headers = {}
        etag = self.db.get(self.make_key('etag', url=url))
        if etag:
            headers['If-None-Match'] = etag.decode('utf-8') if isinstance(etag, bytes) else etag
        last_modified = self.db.get(self.make_key('lm', url=url))
        if last_modified:
            headers['If-Modified-Since'] = (
                last_modified.decode('utf-8') if isinstance(last_modified, bytes)
                else last_modified
                )
        return headers

    @staticmethod
    def _parse_max_age(cache_control):
        """ Extract max-age from a Cache-Control header string and return it as a timedelta, or None. """
        for part in cache_control.split(','):
            part = part.strip()
            if part.startswith('max-age='):
                try:
                    return timedelta(seconds=int(part.split('=', 1)[1]))
                except (ValueError, IndexError):
                    pass
        return None
