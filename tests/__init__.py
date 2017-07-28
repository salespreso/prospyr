# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import json
import os
from functools import wraps
from hashlib import sha256
from random import random

import mock
from requests import Response, codes

from prospyr.connection import _connections, connect


def load_fixture_json(name):
    here = os.path.dirname(__file__)
    path = os.path.join(here, name)
    with open(path, mode='r') as src:
        content = src.read()
    return content


def reset_conns(fn):
    """
    Clear any connections currently configured.
    """
    @wraps(fn)
    def wrapped(*args, **kwargs):
        try:
            fn(*args, **kwargs)
        finally:
            for key in list(_connections):
                del _connections[key]
    return wrapped


def make_cn_with_resp(method, status_code, content, name=None):
    """
    A connection which returns a canned response for one particular verb.

    Content will be JSON-serialised. The verb-method is mocked so assertions
    can be made against it.

    cn = make_cn_with_resp('get', 200, 'Hello World')
    # ... run code under test which calls cn.get(...)
    cn.get.assert_called_with(*expected_args)
    """
    name = name or sha256(str(random()).encode()).hexdigest()
    resp = Response()
    resp._content = json.dumps(content).encode('utf-8')
    resp.status_code = status_code
    cn = connect(email='foo', token='bar', name=name)
    setattr(cn, method, mock.Mock(return_value=resp))
    return cn


class MockSession(object):
    """
    A pretend Session that 200 OKs the content of `urls`.

        conn.session = MockSession({
            'https://google.com/search/': '{"foo": "bar"}'
        })

    A URL's content may also be a two-tuple of (status code, content)

    Anything not in `urls` is 404 Not Founded.
    """
    def __init__(self, urls):
        self.urls = urls

    def _method(self, url, *args, **kwargs):
        success = url in self.urls
        content = self.urls.get(url, '')
        if isinstance(content, tuple):
            code, content = content
        else:
            code = codes.ok if success else codes.not_found
        resp = Response()
        resp._content = content.encode('utf-8')
        resp.status_code = code
        return resp

    def get(self, url, *args, **kwargs):
        return self._method(url, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        return self._method(url, *args, **kwargs)

    def put(self, url, *args, **kwargs):
        return self._method(url, *args, **kwargs)

    def delete(self, url, *args, **kwargs):
        return self._method(url, *args, **kwargs)


def make_cn_with_resps(urls, name='default'):
    """
    A connection that 200 OKs the content of `urls`.

    A URL's content may also be a two-tuple of (status code, content)

    Anything not in `urls` is 404 Not Founded.
    """
    cn = connect(email='foo', token='bar', name=name)
    urls = {cn.build_absolute_url(p): r for p, r in urls.items()}
    cn.session = MockSession(urls)
    cn.get = mock.Mock(wraps=cn.get)
    cn.post = mock.Mock(wraps=cn.post)
    cn.put = mock.Mock(wraps=cn.put)
    cn.delete = mock.Mock(wraps=cn.delete)
    return cn
