# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import arrow
from arrow.parser import ParserError
from marshmallow import ValidationError, fields
from marshmallow.utils import missing as missing_

from prospyr.util import import_dotted_path


class Unix(fields.Field):
    """
    datetime.datetime <-> unix timestamp
    """
    def _serialize(self, value, attr, obj):
        try:
            return arrow.get(value).timestamp
        except ParserError as ex:
            raise ValidationError(ex)

    def _deserialize(self, value, attr, obj):
        try:
            return arrow.get(value).datetime
        except ParserError as ex:
            raise ValidationError(ex)


class NestedResource(fields.Field):
    """
    Represent a nested data structure as a Resource instance.

    If many=True, a listlike data structure is expected instead. If
    id_only=True, only the id field must exist in the nested representation;
    the remainder of the Resource's data will be fetched.
    """

    def __init__(self, resource_cls, default=missing_, many=False,
                 id_only=False, **kwargs):
        self.resource_cls = resource_cls
        self.schema = type(resource_cls.Meta.schema)
        self.many = many
        self.id_only = id_only
        super(NestedResource, self).__init__(default=default, many=many,
                                             **kwargs)

    def _deserialize(self, value, attr, data):
        if not self.many:
            value = [value]

        resources = []
        for v in value:
            if self.id_only:
                resources.append(self.resource_cls.objects.get(id=v['id']))
            else:
                resources.append(self.resource_cls.from_api_data(v))

        return resources if self.many else resources[0]

    def _serialize(self, value, attr, data):
        if self.many:
            return [v._raw_data for v in value]
        else:
            return value._raw_data


class NestedIdentifiedResource(fields.Field):
    """
    (De)serialize "Identifier" fields as Resource instances.

    See:
        https://www.prosperworks.com/developer_api/identifier
    """

    _default_types = {
        'person': 'prospyr.resources.Person',
        # 'lead': 'Lead',  # TODO
        'opportunity': 'prospyr.resources.Opportunity',
        'company': 'prospyr.resources.Company',
    }

    def __init__(self, default=missing_, many=False, types=None, **kwargs):
        self.many = many
        self.types = self._default_types if types is None else types
        self.reverse_types = {v: k for k, v in self.types.items()}
        super(NestedIdentifiedResource, self).__init__(default=default,
                                                       many=many, **kwargs)

    def _deserialize(self, value, attr, data):
        if not self.many:
            value = [value]

        resources = []
        for v in value:
            resource_cls = import_dotted_path(self.types.get(v['type']))
            if resource_cls is None:
                raise ValueError('Unknown identifier type %s' % v['type'])
            resource = resource_cls.objects.get(id=v['id'])
            resources.append(resource)

        return resources if self.many else resources[0]

    def _serialize(self, value, attr, data):
        if not self.many:
            value = [value]

        from prospyr.resources import Identifier  # avoid circular derp

        raws = []
        for v in value:
            raw = Identifier.from_instance(v)
            raws.append(raw._raw_data)
        return raws if self.many else raws[0]
