# -*- coding: utf-8 -*-

from __future__ import division, print_function, unicode_literals

import re


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

assert to_snake('FooBar') == 'foo_bar'
assert to_snake('foo-bar') == 'foo_bar'
assert to_snake('foo_bar') == 'foo_bar'


def to_kebab(string):
    """
    Converts `string` to kebab-case.
    """
    return '-'.join(_parts(string))

assert to_kebab('FooBar') == 'foo-bar'
assert to_kebab('foo-bar') == 'foo-bar'
assert to_kebab('foo_bar') == 'foo-bar'


def to_camel(string):
    """
    Converts `string` to CamelCase.
    """
    return ''.join(p.title() for p in _parts(string))

assert to_camel('FooBar') == 'FooBar'
assert to_camel('foo-bar') == 'FooBar'
assert to_camel('foo_bar') == 'FooBar'
