# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import mock
from nose.tools import assert_raises

from prospyr.connection import Connection, connect, get, url_join, validate_url
from prospyr.exceptions import MisconfiguredError
from tests import reset_conns


@reset_conns
def test_create_connection():
    connect('address@example.org', 'token')


@reset_conns
def test_cannot_clobber_name():
    connect('address@example.org', 'token', name='foo')
    with assert_raises(ValueError):
        connect('address@example.org', 'token', name='foo')

    # changing email addr shouldn't make a difference
    with assert_raises(ValueError):
        connect('other_address@example.org', 'token', name='foo')

    # nor token
    with assert_raises(ValueError):
        connect('address@example.org', 'token2', name='foo')


@reset_conns
def test_can_get_by_name():
    connect('address@example.org', 'token', name='foo')
    get('foo')


@reset_conns
def test_cannot_get_by_name_if_does_not_exist():
    connect('address@example.org', 'token', name='foo')
    with assert_raises(MisconfiguredError):
        get('bar')

    with assert_raises(MisconfiguredError):
        get()


def test_api_url_validation():
    assert validate_url('https://api.prosperworks.com/developer_api/')

    invalids = (
        '/developer_api/',
        'ftp://api.prosperworks.com/developer_api/',
        'http://:3000/path/somewhere',
        'https://api.prosperworks.com/developer_api/v1/',
        'localhost:3000',
        'user@example.org',
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


def test_http_verbs():
    cn = Connection(url='url', email='email', token='token')
    mock_session = mock.Mock()
    cn.session = mock_session
    verbs = 'put', 'post', 'patch', 'options', 'delete', 'get'
    for verb in verbs:
        assert hasattr(cn, verb)
        method = getattr(cn, verb)
        method('url', test_method=verb)
        session_method = getattr(mock_session, verb)
        session_method.assert_called_with('url', test_method=verb)


def test_build_absolute_url():
    cn = Connection(url='url', email='email', token='token')
    cn.api_url = 'https://hostname.tld/foo/'
    expected = cn.build_absolute_url('bar/baz')
    assert expected == 'https://hostname.tld/foo/bar/baz'
