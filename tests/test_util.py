import sys

from nose.tools import assert_raises

from prospyr.util import (import_dotted_path, seconds, to_camel, to_kebab,
                          to_snake)

CONSTANT = 'foo'


def test_to_snake():
    assert to_snake('FooBar') == 'foo_bar'
    assert to_snake('foo-bar') == 'foo_bar'
    assert to_snake('foo_bar') == 'foo_bar'


def test_to_kebab():
    assert to_kebab('FooBar') == 'foo-bar'
    assert to_kebab('foo-bar') == 'foo-bar'
    assert to_kebab('foo_bar') == 'foo-bar'


def test_to_camel():
    assert to_camel('FooBar') == 'FooBar'
    assert to_camel('foo-bar') == 'FooBar'
    assert to_camel('foo_bar') == 'FooBar'


def test_seconds():
    assert seconds(minutes=1) == 60
    assert seconds(seconds=1) == 1
    assert seconds(hours=2) == 60 * 60 * 2


def test_import_dotted_path():
    assert import_dotted_path('tests.test_util.CONSTANT') == 'foo'
    assert import_dotted_path('tests.test_util') is sys.modules[__name__]
    assert import_dotted_path('tests.test_util.test_import_dotted_path') is test_import_dotted_path  # noqa

    with assert_raises(ImportError):
        import_dotted_path('ohsdfojhsdf.sdfosdhkjshdfsdf.sdfohsdjohsdf')
