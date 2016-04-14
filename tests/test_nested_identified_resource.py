import mock
from marshmallow import fields
from nose.tools import assert_raises

from prospyr.exceptions import ValidationError
from prospyr.resources import NestedIdentifiedResource, Resource

types = {'child': 'tests.test_nested_identified_resource.Child'}


class NoneableParent(Resource):
    class Meta:
        pass
    child = NestedIdentifiedResource(types=types, allow_none=True)
    children = NestedIdentifiedResource(types=types, many=True,
                                        allow_none=True)


class Parent(Resource):
    class Meta:
        pass
    child = NestedIdentifiedResource(types=types)
    children = NestedIdentifiedResource(types=types, many=True)


class Child(Resource):
    class Meta:
        pass
    id = fields.Integer()


deserialised = Parent(
    child=Child(id=1),
    children=[
        Child(id=2),
        Child(id=3),
    ]
)


serialised = {
    'child': {'type': 'child', 'id': 1},
    'children': [
        {'type': 'child', 'id': 2},
        {'type': 'child', 'id': 3},
    ]
}


def test_serialise():
    with mock.patch('prospyr.resources.Identifier.valid_types', {'child'}):
        assert deserialised._raw_data == serialised


def test_deserialise():
    patch_path = 'tests.test_nested_identified_resource.Child.objects.get'
    with mock.patch(patch_path) as get:
        get.side_effect = lambda id: {'type': 'child', 'id': id}
        actual = Parent.from_api_data(serialised)
    get.assert_any_call(id=1)
    get.assert_any_call(id=2)
    get.assert_any_call(id=3)
    assert actual.child == serialised['child']
    assert actual.children == serialised['children']


def test_allow_none():
    raw = {
        'child': {'type': None, 'id': None},
        'children': [
            {'type': None, 'id': None},
            {'type': None, 'id': None}
        ]
    }
    with assert_raises(ValidationError):
        Parent.from_api_data(raw)

    actual = NoneableParent.from_api_data(raw)
    assert actual.child is None
    assert actual.children == [None, None]

    with assert_raises(ValidationError):
        Parent(child=None, children=[None, None, None])._raw_data

    cooked = NoneableParent(
        child=None,
        children=[None, None, None]
    )

    assert cooked._raw_data == {
        'child': {'type': None, 'id': None},
        'children': [
            {'type': None, 'id': None},
            {'type': None, 'id': None},
            {'type': None, 'id': None},
        ]
    }
