# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import json

from nose.tools import assert_raises
from requests import Response, codes

from prospyr import connect, exceptions
from prospyr.resources import Person
from prospyr.schema import EmailSchema
from tests import MockSession, load_fixture_json, reset_conns

Email = EmailSchema().namedtuple_class


def assert_is_jon(alleged_jon):
    """
    Checked that `alleged_jon` looks like Jon from person.json.
    """
    assert alleged_jon.name == 'Jon Lee'
    assert alleged_jon.details == 'Founder of the simple CRM for Google Apps'
    assert set(alleged_jon.emails) == {
        Email(email='support@prosperworks.com', category='work'),
        Email(email='support_1@prosperworks.com', category='work'),
    }
    return True


@reset_conns
def test_read():
    cn = connect(email='foo', token='bar')
    cn.session = MockSession(urls={
        cn.build_absolute_url('people/1/'): load_fixture_json('person.json'),
        cn.build_absolute_url('custom_field_definitions/'): load_fixture_json('custom_field_defs.json')  # noqa
    })
    jon = Person(id=1)
    jon.read()
    assert_is_jon(jon)


@reset_conns
def test_manager_get():
    cn = connect(email='foo', token='bar')
    cn.session = MockSession(urls={
        cn.build_absolute_url('people/1/'): load_fixture_json('person.json')
    })
    jon = Person.objects.get(id=1)
    assert_is_jon(jon)


def test_no_instance_access_to_manager():
    # accessing from class is OK
    Person.objects

    # but cannot access from class instance
    person = Person()
    with assert_raises(AttributeError):
        person.objects


@reset_conns
def test_manager_connection_assignment():
    cn_without_jon = connect(email='foo', token='bar', name='without_jon')
    cn_with_jon = connect(email='foo', token='bar', name='with_jon')

    cn_without_jon.session = MockSession(urls={})
    cn_with_jon.session = MockSession(urls={
        cn_with_jon.build_absolute_url('people/1/'): load_fixture_json('person.json')  # noqa
    })

    jon = Person.objects.use('with_jon').get(id=1)
    assert_is_jon(jon)
    with assert_raises(exceptions.ApiError):
        jon = Person.objects.use('without_jon').get(id=1)


def test_resource_validation():
    # valid albert
    albert = Person(name='Albert Cornswaddle', emails=[])
    albert.validate()

    # albert without email
    albert = Person(name='Albert Cornswaddle')
    with assert_raises(exceptions.ValidationError):
        albert.validate()


@reset_conns
def test_construct_from_api_data():
    cn = connect(email='foo', token='bar', name='default')
    cn.session = MockSession(urls={
        cn.build_absolute_url('custom_field_definitions/'): load_fixture_json('custom_field_defs.json')  # noqa
    })

    data = json.loads(load_fixture_json('person.json'))
    jon = Person.from_api_data(data)
    assert_is_jon(jon)

    data = {'invalid': 'data'}
    with assert_raises(exceptions.ValidationError):
        Person.from_api_data(data)


def test_repr_does_not_raise():
    people = (
        Person(),
        Person(id=12),
        Person(name='Gertrude T. Boondock'),
    )
    for person in people:
        print(repr(person))


def test_str_does_not_raise():
    people = (
        Person(),
        Person(id=12),
        Person(name='Gertrude T. Boondock'),
    )
    for person in people:
        print(str(person))


@reset_conns
def test_id_or_email_required_for_person():
    cn = connect(email='foo', token='bar')
    cn.session = MockSession(urls={
        cn.build_absolute_url('people/1/'): load_fixture_json('person.json')
    })
    with assert_raises(exceptions.ProspyrException):
        Person.objects.get()


@reset_conns
def test_get_person_by_email():
    cn = connect(email='foo', token='bar')
    cn.session = MockSession(urls={
        cn.build_absolute_url('people/fetch_by_email/'): load_fixture_json('person.json')  # noqa
    })
    person = Person.objects.get(email='support@prosperworks.com')
    assert_is_jon(person)
