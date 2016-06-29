# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import json

import mock
from marshmallow import fields
from nose.tools import assert_raises
from requests import Response, codes

from prospyr.connection import connect
from prospyr.exceptions import ValidationError
from prospyr.resources import Resource
from prospyr.search import ActivityTypeListSet, ListSet, ResultSet
from tests import load_fixture_json, reset_conns


class MockManager(object):
    resource_cls = 'foo'


def test_immutable():
    rs = ResultSet(
        resource_cls=mock.Mock(**{'Meta.order_fields': {'foo'}})
    )
    rs_filtered = rs.filter(foo='bar')
    rs_ordered = rs.order_by('foo')
    assert rs is not rs_filtered
    assert rs is not rs_ordered


def test_all_aliases_argless_filter():
    rs = mock.Mock(spec=ResultSet)
    ResultSet.all(rs)
    rs.filter.assert_called_with()  # no args


def test_orderby():
    resource_cls = mock.Mock(**{
        'Meta.order_fields': {'one', 'two'}
    })
    rs = ResultSet(resource_cls=resource_cls)
    one_forwards = rs.order_by('one')._build_query()
    assert one_forwards['sort_by'] == 'one'
    assert one_forwards['sort_direction'] == 'asc'

    one_backwards = rs.order_by('-one')._build_query()
    assert one_backwards['sort_by'] == 'one'
    assert one_backwards['sort_direction'] == 'desc'

    two_forwards = rs.order_by('two')._build_query()
    assert two_forwards['sort_by'] == 'two'
    assert two_forwards['sort_direction'] == 'asc'

    two_backwards = rs.order_by('-two')._build_query()
    assert two_backwards['sort_by'] == 'two'
    assert two_backwards['sort_direction'] == 'desc'

    with assert_raises(ValueError):
        rs.order_by('invalid')

    with assert_raises(ValueError):
        rs.order_by('-invalid')


class IdResource(Resource):
    class Meta:
        search_path = 'foo'
    id = fields.Integer()


def json_to_resp(data, status_code=codes.ok):
    resp = Response()
    resp._content = json.dumps(data).encode('utf-8')
    resp.status_code = status_code
    return resp


@reset_conns
def test_iterable():
    """
    Check that ResultSet iterates over result pages
    """
    # 3 pages of results
    pages = (
        json_to_resp([{'id': 1}, {'id': 2}]),
        json_to_resp([{'id': 3}, {'id': 4}]),
        json_to_resp([{'id': 5}, {'id': 6}]),
    )
    cn = connect(email='foo', token='bar')
    cn.session.post = mock.Mock(side_effect=pages)
    rs = ResultSet(resource_cls=IdResource, page_size=2)
    assert {r.id for r in rs} == {1, 2, 3, 4, 5, 6}


@reset_conns
def test_finish_on_small_page():
    """
    ResultSet should detect it is on the last page of results.
    """
    # A page of 2 results, then a second with 1 result. The exception should
    # not be called.
    def pages(*args, **kwargs):
        yield json_to_resp([{'id': 1}, {'id': 2}])
        yield json_to_resp([{'id': 3}])
        raise Exception('ResultSet queried too many pages')

    cn = connect(email='foo', token='bar')
    cn.session.post = mock.Mock(side_effect=pages())
    rs = ResultSet(resource_cls=IdResource, page_size=2)
    assert {r.id for r in rs} == {1, 2, 3}


@reset_conns
def test_last_page_is_exactly_page_size():
    """
    Should finish cleanly if last page is full yet there are no more results.
    """
    # A page of 2 results, then a second with 1 result. The exception should
    # not be called.
    def pages(*args, **kwargs):
        yield json_to_resp([{'id': 1}, {'id': 2}])
        yield json_to_resp([{'id': 3}, {'id': 4}])

        # PW returns 200 OK and empty list, not 404, when past last page.
        yield json_to_resp([])

    cn = connect(email='foo', token='bar')
    cn.session.post = mock.Mock(side_effect=pages())
    rs = ResultSet(resource_cls=IdResource, page_size=2)
    assert {r.id for r in rs} == {1, 2, 3, 4}


def fibs_to(n):
    a, b = 0, 1
    while a <= n:
        yield a
        a, b = b, a + b


def test_slicing():
    rs = ResultSet(resource_cls='foo')
    rs._results = fibs_to(13)
    assert rs[0] == 0
    assert rs[1] == 1
    assert rs[2] == 1
    assert rs[3] == 2
    assert rs[4] == 3
    assert rs[5] == 5
    assert rs[6] == 8
    assert rs[7] == 13

    assert rs[0:13] == [0, 1, 1, 2, 3, 5, 8, 13]
    assert rs[0:1000] == [0, 1, 1, 2, 3, 5, 8, 13]  # per convention
    assert rs[1:] == [1, 1, 2, 3, 5, 8, 13]
    assert rs[:1] == [0]

    # no negative indexing
    with assert_raises(IndexError):
        rs[0:-1]
    with assert_raises(IndexError):
        rs[-3:-1]
    with assert_raises(IndexError):
        rs[-1]

    # out of range
    with assert_raises(IndexError):
        rs[100]


class ReprResource(Resource):
    class Meta:
        pass
    pass


def test_repr():
    rs = ResultSet(resource_cls=ReprResource)
    rs._results = range(20)
    assert repr(rs) == '<ResultSet: 0, 1, 2, 3, 4, ...>', repr(rs)

    rs._results = range(3)
    assert repr(rs) == '<ResultSet: 0, 1, 2>', repr(rs)


def test_cannot_filter_listset():
    with assert_raises(NotImplementedError) as cm:
        ListSet(resource_cls=None).filter()
    # msg should mention filtering by name
    assert any('filtering' in arg for arg in cm.exception.args)


def test_cannot_order_listset():
    with assert_raises(NotImplementedError) as cm:
        ListSet(resource_cls=None).order_by()
    # msg should mention ordering by name
    assert any('ordering' in arg for arg in cm.exception.args)


def test_activitytype_listset():
    connect(email='foo', token='bar')
    atls = ActivityTypeListSet()
    resp = Response()
    resp._content = load_fixture_json('activity_types.json').encode('utf-8')
    resp.status_code = codes.ok
    with mock.patch('prospyr.connection.Connection.get') as get:
        get.return_value = resp
        actual = list(atls)

    actual_names = {a.name for a in actual}
    assert actual_names == {
        'Note', 'Phone Call', 'Meeting', 'Property Changed',
        'My Custom Activity Type', 'Pipeline Stage Changed'
    }


@reset_conns
def test_storing_invalid_resources():
    remote_data = json_to_resp([{'id': 1}, {'id': 'not-an-integer'}])
    cn = connect(email='foo', token='bar')
    cn.session.post = mock.Mock(side_effect=[remote_data])

    # 'not-an-integer' fails integer validation and raises
    with assert_raises(ValidationError):
        list(ResultSet(resource_cls=IdResource))

    # with store_invalid, no exception is raised
    cn.session.post = mock.Mock(side_effect=[remote_data])
    invalid = []
    valid = list(ResultSet(resource_cls=IdResource).store_invalid(invalid))
    assert len(valid) == 1  # id 1 passed validation
    assert len(invalid) == 1  # id 'not-an-integer' didn't
