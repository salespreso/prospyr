import mock
from marshmallow import fields

from prospyr.resources import NestedIdentifiedResource, Resource
from tests import make_cn_with_resp

types = {'child': 'tests.test_nested_identified_resource.Child'}


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


def test_nested_identified_resource_serialise():
    with mock.patch('prospyr.resources.Identifier.valid_types', {'child'}):
        assert deserialised._raw_data == serialised


def test_nested_identified_resource_deserialise():
    patch_path = 'tests.test_nested_identified_resource.Child.objects.get'
    with mock.patch(patch_path) as get:
        get.side_effect = lambda id: {'type': 'child', 'id': id}
        actual = Parent.from_api_data(serialised)
    get.assert_any_call(id=1)
    get.assert_any_call(id=2)
    get.assert_any_call(id=3)
    assert actual.child == serialised['child']
    assert actual.children == serialised['children']
