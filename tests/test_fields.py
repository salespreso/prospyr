# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from datetime import timedelta

import arrow
from marshmallow import Schema

from prospyr.fields import NestedResource, Unix
from prospyr.resources import PipelineStage


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


class MultipleParent(Schema):
    stage = NestedResource(PipelineStage, many=True)


def test_load_single_nested_resource():
    schema = SingleParent()
    data = {
        'stage': {
            'name': 'foo',
        }
    }
    loaded, _ = schema.load(data)
    assert isinstance(loaded['stage'], PipelineStage)
    assert loaded['stage'].name == 'foo'


def test_load_multiple_nested_resource():
    schema = MultipleParent()
    data = {
        'stage': [
            {'name': 'foo'},
            {'name': 'bar'}
        ]
    }
    loaded, _ = schema.load(data)
    assert all(isinstance(s, PipelineStage) for s in loaded['stage'])
    assert {s.name for s in loaded['stage']} == {'foo', 'bar'}


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
