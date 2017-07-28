# -*- coding: utf-8 -*-
"""
This test module uses a pale imitation of the ProsperWorks API to test CRUD
methods.
"""

from __future__ import absolute_import, print_function, unicode_literals

from nose.tools import assert_raises
from requests import codes
from urlobject import URLObject

from prospyr.connection import _default_url
from prospyr.resources import Person
from tests import load_fixture_json, make_cn_with_resps, reset_conns


@reset_conns
def test_create():
    # can create
    cn = make_cn_with_resps({
        'people/': load_fixture_json('person.json'),
        'custom_field_definitions/': load_fixture_json('custom_field_defs.json'),  # noqa
    })
    person = Person(name='Slithey Tove')
    person.create(using=cn.name)
    expected_url = URLObject(_default_url + 'v1/people/')
    cn.post.assert_called_with(expected_url, json={'name': 'Slithey Tove'})


@reset_conns
def test_cannot_create_with_id():
    cn = make_cn_with_resps({
        'people/': load_fixture_json('person.json'),
    })
    # can't create with an ID
    with assert_raises(ValueError):
        id_person = Person(id=1)
        id_person.create(using=cn.name)


@reset_conns
def test_validation_errors_raised_during_create():
    # validation errors come back. note the `invalid` instance isn't really
    # invalid; we just simulate the invalid response.
    invalid = Person(name='Invalid')
    cn = make_cn_with_resps({
        'people/': (codes.unprocessable_entity, '{"message": "Something wrong"}'),  # noqa
    })
    try:
        invalid.create(using=cn.name)
    except ValueError as ex:
        assert 'Something wrong' in str(ex)
    else:
        raise AssertionError('Exception not thrown')


@reset_conns
def test_delete():
    cn = make_cn_with_resps({
        'people/1/': ''
    })
    person = Person(id=1)
    person.delete(using=cn.name)
    expected_url = URLObject(_default_url + 'v1/people/1/')
    cn.delete.assert_called_with(expected_url)

    # can't delete without an id
    with assert_raises(ValueError):
        no_id_person = Person()
        no_id_person.delete(using=cn.name)


@reset_conns
def test_update():
    cn = make_cn_with_resps({
        'people/1/': load_fixture_json('person.json'),
    })
    person = Person(id=1, name='Nantucket Terwilliger')
    person.update(using=cn.name)
    expected_url = URLObject(_default_url + 'v1/people/1/')
    cn.put.assert_called_with(
        expected_url,
        json={'name': 'Nantucket Terwilliger'}
    )


@reset_conns
def test_cannot_update_without_an_id():
    # can't update without an id
    cn = make_cn_with_resps(urls={})
    with assert_raises(ValueError):
        no_id_person = Person()
        no_id_person.update(using=cn.name)


@reset_conns
def test_validation_errors_raised_during_update():
    # validation errors come back. note the `invalid` instance isn't really
    # invalid; we just simulate the invalid response.
    invalid = Person(id=1, name='Invalid')
    cn = make_cn_with_resps({
        'people/1/': (codes.unprocessable_entity, '{"message": "Something wrong"}'),  # noqa
    })
    try:
        invalid.update(using=cn.name)
    except ValueError as ex:
        assert 'Something wrong' in str(ex)
    else:
        raise AssertionError('Exception not thrown')
