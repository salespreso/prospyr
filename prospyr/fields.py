# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import arrow
from arrow.parser import ParserError
from marshmallow import ValidationError, fields
from marshmallow.utils import missing as missing_


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

    def __init__(self, resource_cls, default=missing_, many=False, **kwargs):
        self.resource_cls = resource_cls
        self.schema = type(resource_cls.Meta.schema)
        self.many = many
        super(NestedResource, self).__init__(default=default, many=many,
                                             **kwargs)

    def _deserialize(self, value, attr, data):
        if self.many:
            return [self.resource_cls.from_api_data(v) for v in value]
        else:
            return self.resource_cls.from_api_data(value)

    def _serialize(self, value, attr, data):
        if self.many:
            return [v._raw_data for v in value]
        else:
            return value._raw_data
