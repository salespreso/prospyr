# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import os
from functools import wraps

from prospyr.connection import _connections


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
