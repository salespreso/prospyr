# -*- coding: utf-8 -*-
"""
This test module uses a pale imitation of the ProsperWorks API to test CRUD
methods.
"""

from __future__ import absolute_import, print_function, unicode_literals

import json
from hashlib import sha256
from random import random

import mock
from nose.tools import assert_raises
from requests import Response, codes
from urlobject import URLObject

from prospyr.connection import _default_url, connect
from prospyr.resources import Person
from tests import load_fixture_json, reset_conns


def make_cn_with_resp(method, status_code, content):
    """
    A connection which returns a canned response for one particular verb.

    Content will be JSON-serialised. The verb-method is mocked so assertions
    can be made against it.

    cn = make_cn_with_resp('get', 200, 'Hello World')
    # ... run code under test which calls cn.get(...)
    cn.get.assert_called_with(*expected_args)
    """
    name = sha256(str(random()).encode()).hexdigest()
    resp = Response()
    resp._content = json.dumps(content).encode('utf-8')
    resp.status_code = status_code
    cn = connect(email='foo', token='bar', name=name)
    setattr(cn, method, mock.Mock(return_value=resp))
    return cn


@reset_conns
def test_create():
    # can create
    content = json.loads(load_fixture_json('person.json'))
    cn = make_cn_with_resp(
        method='post',
        status_code=codes.ok,
        content=content
    )
    person = Person(name='Slithey Tove')
    person.create(using=cn.name)
    expected_url = URLObject(_default_url + 'v1/people/')
    cn.post.assert_called_with(expected_url, json={'name': 'Slithey Tove'})

    # can't create with an ID
    with assert_raises(ValueError):
        id_person = Person(id=1)
        id_person.create(using=cn.name)

    # validation errors come back. note the `invalid` instance isn't really
    # invalid; we just simulate the invalid response.
    invalid = Person(name='Invalid')
    cn = make_cn_with_resp(
        method='post',
        status_code=codes.unprocessable_entity,
        content=dict(message='Something wrong')
    )
    try:
        invalid.create(using=cn.name)
    except ValueError as ex:
        assert 'Something wrong' in str(ex)
    else:
        raise AssertionError('Exception not thrown')


@reset_conns
def test_delete():
    cn = make_cn_with_resp(method='delete', status_code=codes.ok, content=[])
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
    content = json.loads(load_fixture_json('person.json'))
    cn = make_cn_with_resp(method='put', status_code=codes.ok, content=content)
    person = Person(id=1, name='Nantucket Terwilliger')
    person.update(using=cn.name)
    expected_url = URLObject(_default_url + 'v1/people/1/')
    cn.put.assert_called_with(
        expected_url,
        json={'name': 'Nantucket Terwilliger'}
    )

    # can't update without an id
    with assert_raises(ValueError):
        no_id_person = Person()
        no_id_person.update(using=cn.name)

    # validation errors come back. note the `invalid` instance isn't really
    # invalid; we just simulate the invalid response.
    invalid = Person(id=1, name='Invalid')
    cn = make_cn_with_resp(
        method='put',
        status_code=codes.unprocessable_entity,
        content=dict(message='Something wrong')
    )
    try:
        invalid.update(using=cn.name)
    except ValueError as ex:
        assert 'Something wrong' in str(ex)
    else:
        raise AssertionError('Exception not thrown')
