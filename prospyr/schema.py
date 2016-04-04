# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from collections import Mapping, namedtuple

import arrow
from arrow.parser import ParserError
from marshmallow import (Schema, ValidationError, fields, post_dump, post_load,
                         pre_dump)


class TrimSchema(Schema):
    """
    A schema which does not dump "empty" fields.

    ...where empty is defined as None for value fields, and an empty list for
    collection fields.

    This is in line with the behaviour ProsperWorks expects.
    """

    @post_dump
    def clean_empty(self, data):
        to_clean = []
        for key, value in data.items():
            collection = getattr(self.fields[key], 'many', False)
            if collection and value == []:
                to_clean.append(key)
            elif value is None:
                to_clean.append(key)

        for key in to_clean:
            data.pop(key)

        return data


class NamedTupleSchema(Schema):
    """
    (De)serialise to namedtuple instead of dict
    """
    def __init__(self, *args, **kwargs):
        super(NamedTupleSchema, self).__init__(*args, **kwargs)
        name = type(self).__name__.replace('Schema', '')
        fields = self.declared_fields.keys()
        self.namedtuple_class = namedtuple(name, fields)

    @post_load
    def to_namedtuple(self, data):
        return self.namedtuple_class(**data)

    @pre_dump
    def from_namedtuple(self, obj):
        if not isinstance(obj, Mapping):
            return obj._asdict()
        return obj


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


class EmailSchema(NamedTupleSchema):
    email = fields.Email()
    category = fields.String()


class WebsiteSchema(Schema):
    website = fields.Url()
    category = fields.String()


class SocialSchema(Schema):
    website = fields.Url()
    category = fields.String()


class PhoneNumberSchema(Schema):
    number = fields.String()
    category = fields.String()


class CustomFieldSchema(Schema):
    custom_field_definition_id = fields.Integer()
    value = fields.String()  # TODO base this on field definition


class AddressSchema(Schema):
    street = fields.String(allow_none=True)
    city = fields.String(allow_none=True)
    state = fields.String(allow_none=True)
    postal_code = fields.String(allow_none=True)
    country = fields.String(allow_none=True)
