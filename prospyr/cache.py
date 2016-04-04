# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from collections import namedtuple
from logging import getLogger

import arrow

logger = getLogger(__name__)
CacheEntry = namedtuple('CacheEntry', 'value,created,max_age')


class InMemoryCache(object):
    """
    An in-memory cache. Keys are expired by count and age.
    """

    def __init__(self, size=500):
        self._cache = {}
        self._size = size

    def meta(self, key):
        return self._cache[key]

    def set(self, key, value, max_age=0):
        now = arrow.utcnow().timestamp
        entry = CacheEntry(value=value, created=now, max_age=max_age)
        logger.debug('%s added to cache', key)
        self._cache[key] = entry
        self._maintenance()
        return True

    def get(self, key):
        self._maintenance()
        try:
            entry = self._cache[key]
            logger.debug('Cache hit for %s', key)
            return entry.value
        except KeyError:
            logger.debug('Cache miss for %s', key)
            return None

    def clear(self, key):
        if key in self._cache:
            logger.debug('Cleared %s', key)
            self._cache.pop(key)
        return True

    def _maintenance(self):
        # expire any keys older than max_age
        to_expire = []
        now = arrow.utcnow().timestamp
        for key, entry in self._cache.items():
            too_old = (
                entry.max_age and
                entry.created + entry.max_age <= now
            )
            if too_old:
                to_expire.append(key)
        for key in to_expire:
            logger.debug('%s has expired', key)
            del self._cache[key]

        # if too many keys, repeatedly expire oldest
        excess_size = len(self._cache) - self._size
        if excess_size > 0:
            key_ages = [(created, key)
                        for key, (_, created, _) in self._cache.items()]
            key_ages = sorted(key_ages)
            for _, key in key_ages[:excess_size]:
                logger.debug('Cache too full, evicted %s', key)
                del self._cache[key]


class NoOpCache(object):
    """
    A cache class which doesn't cache anything.
    """

    def meta(self, key):
        return None

    def set(self, key, value, max_age=0):
        return True

    def get(self, key):
        return None

    def clear(self, key):
        return True
