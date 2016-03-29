# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from nose.tools import assert_raises

from prospyr.connection import (_connections, connect, get, url_join,
                                validate_url)
from prospyr.exceptions import MisconfiguredError


def reset_conns():
    for key in list(_connections):
        del _connections[key]


def test_create_connection():
    reset_conns()
    connect('address@example.org', 'token')


def test_cannot_clobber_name():
    reset_conns()
    connect('address@example.org', 'token', name='foo')
    with assert_raises(ValueError):
        connect('address@example.org', 'token', name='foo')

    # changing email addr shouldn't make a difference
    with assert_raises(ValueError):
        connect('other_address@example.org', 'token', name='foo')

    # nor token
    with assert_raises(ValueError):
        connect('address@example.org', 'token2', name='foo')


def test_can_get_by_name():
    reset_conns()
    connect('address@example.org', 'token', name='foo')
    get('foo')


def test_cannot_get_by_name_if_does_not_exist():
    reset_conns()
    connect('address@example.org', 'token', name='foo')
    with assert_raises(MisconfiguredError):
        get('bar')


def test_api_url_validation():
    assert validate_url('https://api.prosperworks.com/developer_api/')

    invalids = (
        'ftp://api.prosperworks.com/developer_api/',
        'localhost:3000',
        'user@example.org',
        '/developer_api/',
        'https://api.prosperworks.com/developer_api/v1/',
    )
    for invalid in invalids:
        with assert_raises(MisconfiguredError):
            validate_url(invalid)


def test_url_join():
    base = 'http://hostname.tld/path/'
    assert url_join(base, 'foo') == 'http://hostname.tld/path/foo'
    assert url_join(base, 'foo/') == 'http://hostname.tld/path/foo/'
    assert url_join(base, 'foo/bar') == 'http://hostname.tld/path/foo/bar'
    assert url_join(base, 'foo/bar/') == 'http://hostname.tld/path/foo/bar/'
    assert url_join(base, '/foo/') == 'http://hostname.tld/foo/'
    assert url_join(base, 'http://qux.org') == 'http://hostname.tld/path/http%3A//qux.org'  # noqa
