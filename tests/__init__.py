# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import json
import os
from functools import wraps
from hashlib import sha256
from random import random

import mock
from requests import Response

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
        for key in list(_connections):
            del _connections[key]
        fn(*args, **kwargs)
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


def make_cn_with_resps(url_map, name=None):
    name = name or sha256(str(random()).encode()).hexdigest()
    cn = connect(email='foo', token='bar', name=name)

    def _get(url):
        status, content = url_map[url]
        resp = Response()
        resp._content = content
        resp.status_code = status
        return resp
    cn.get = _get
