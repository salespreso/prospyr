import arrow

from prospyr.cache import CacheEntry, InMemoryCache, NoOpCache


def test_inmem_set_and_get():
    cache = InMemoryCache()
    cache.set('foo', 'expected')
    assert cache.get('foo') == 'expected'


def test_inmem_clear():
    cache = InMemoryCache()
    cache.set('foo', 'expected')
    cache.clear('foo')
    assert cache.get('foo') is None


def test_trimmed_if_oversize():
    cache = InMemoryCache(size=1)
    cache.set('foo', 1)
    cache.set('bar', 2)
    assert len(cache._cache) == 1

    cache = InMemoryCache(size=2)
    cache.set('foo', 1)
    cache.set('bar', 2)
    cache.set('baz', 3)
    assert len(cache._cache) == 2


def test_trimmed_if_expired():
    cache = InMemoryCache()
    now = arrow.now().timestamp
    cache._cache = {'foo': CacheEntry(
        value='expected',
        created=0,
        max_age=now + 100)
    }
    assert cache.get('foo') == 'expected'

    cache._cache = {'foo': CacheEntry(
        value='expected',
        created=0,
        max_age=1)
    }
    assert cache.get('foo') is None


def test_set_noop():
    cache = NoOpCache()
    cache.set('foo', 'expected')
    assert cache.get('foo') is None


def test_clear_noop():
    cache = NoOpCache()
    cache.set('foo', 'expected')
    cache.clear('foo')
    assert cache.get('foo') is None
