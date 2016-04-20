# -*- coding: utf-8 -*-

from __future__ import division, print_function, unicode_literals

import importlib
import re
import sys
from datetime import timedelta


def _parts(string):
    if '-' in string and '_' not in string:
        parts = string.split('-')
    elif '_' in string and '-' not in string:
        parts = string.split('_')
    else:
        parts = re.findall(r'[A-Z]+[^A-Z]*', string)
    if not parts:
        parts = [string]
    return [p.lower() for p in parts]


def to_snake(string):
    """
    Converts `string` to snake_case.
    """
    return '_'.join(_parts(string))


def to_kebab(string):
    """
    Converts `string` to kebab-case.
    """
    return '-'.join(_parts(string))


def to_camel(string):
    """
    Converts `string` to CamelCase.
    """
    return ''.join(p.title() for p in _parts(string))


def import_dotted_path(path):
    """
    Return the module or name at `path`.
    """
    parts = path.split('.')
    args = []
    found = None

    for l in range(1, len(parts)):
        iterpath = '.'.join(parts[:l])
        attr = parts[l]
        args.append((iterpath, attr))

    for path, attr in args:
        try:
            found = importlib.import_module(path)
        except ImportError:
            pass

        if hasattr(found, attr):
            found = getattr(found, attr)

    if found is None:
        raise ImportError('Cannot import %s', path)

    return found


def seconds(days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0,
            hours=0, weeks=0):
    """
    Convenient time-unit-to-seconds converter. A thin wrapper around timedelta.
    """
    td = timedelta(days=days, seconds=seconds, microseconds=microseconds,
                   milliseconds=milliseconds, minutes=minutes, hours=hours,
                   weeks=weeks)
    return td.total_seconds()


def encode_typename(name):
    """
    Type names must be bytes in Python 2, unicode in Python 3
    """
    if sys.version_info < (3, 0, 0):
        return name.encode('ascii')
    return name
