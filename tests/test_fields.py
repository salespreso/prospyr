# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from datetime import timedelta

import arrow
from marshmallow import Schema
from requests import codes

from prospyr.fields import NestedResource, Unix
from prospyr.resources import PipelineStage
from tests import make_cn_with_resp, reset_conns


class TimeSchema(Schema):
    time = Unix()


def equal_to_second(d1, d2):
    if d1 > d2:
        d2, d1 = d1, d2
    return (d2 - d1) < timedelta(seconds=1)


def test_unix_timestamp_field():
    t = TimeSchema()
    now = arrow.utcnow()

    loaded, _ = t.load(dict(time=now.timestamp))
    dumped, _ = t.dump(dict(time=now))

    # arrow has microseconds, datetime does not; allow for subsecond
    # fidgeywidgey timeywimeyness.
    assert equal_to_second(loaded['time'], now.datetime)
    assert abs(dumped['time'] - now.timestamp) < 1


def test_unix_timestamp_field_validation():
    t = TimeSchema()

    _, errors = t.load(dict(time='potato'))
    assert errors
    assert 'time' in errors
    _, errors = t.dump(dict(time='potato'))
    assert errors
    assert 'time' in errors


class SingleParent(Schema):
    stage = NestedResource(PipelineStage)
    stage_idonly = NestedResource(PipelineStage, id_only=True)


class MultipleParent(Schema):
    stage = NestedResource(PipelineStage, many=True)
    stage_idonly = NestedResource(PipelineStage, many=True, id_only=True)


@reset_conns
def test_load_single_nested_resource():
    stage_3 = {'id': 3, 'name': 'Third Stage'}
    cn = make_cn_with_resp(
        method='get',
        status_code=codes.ok,
        content=[stage_3],
        name='default'
    )
    schema = SingleParent()
    data = {
        'stage': {'name': 'foo'},
        'stage_idonly': {'id': 3},
    }
    loaded, _ = schema.load(data)
    assert isinstance(loaded['stage'], PipelineStage)
    assert loaded['stage'].name == 'foo'
    assert loaded['stage_idonly'].name == 'Third Stage'


def test_load_multiple_nested_resource():
    schema = MultipleParent()
    stage_3_and_4 = [
        {'id': 3, 'name': 'Third Stage'},
        {'id': 4, 'name': 'Fourth Stage'},
    ]
    cn = make_cn_with_resp(
        method='get',
        status_code=codes.ok,
        content=stage_3_and_4,
        name='default'
    )
    data = {
        'stage': [
            {'name': 'foo'},
            {'name': 'bar'}
        ],
        'stage_idonly': [
            {'id': 3},
            {'id': 4},
        ]
    }
    loaded, _ = schema.load(data)
    assert all(isinstance(s, PipelineStage) for s in loaded['stage'])
    assert {s.name for s in loaded['stage']} == {'foo', 'bar'}
    assert {s.name for s in loaded['stage_idonly']} == {'Third Stage', 'Fourth Stage'}  # noqa


def test_dump_single_nested_resource():
    schema = SingleParent()
    data = {
        'stage': PipelineStage(name='foo')
    }
    dumped, _ = schema.dump(data)
    assert dumped['stage'] == {'name': 'foo'}


def test_dump_multiple_nested_resource():
    schema = MultipleParent()
    data = {
        'stage': [
            PipelineStage(name='foo'),
            PipelineStage(name='bar')
        ]
    }
    dumped, _ = schema.dump(data)
    assert {d['name'] for d in dumped['stage']} == {'foo', 'bar'}
