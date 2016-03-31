# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import arrow
from marshmallow import Schema, fields


class Unix(fields.Field):
    """
    datetime.datetime <-> unix timestamp
    """
    def _serialize(self, value, attr, obj):
        return arrow.get(value).timestamp

    def _deserialize(self, value, attr, obj):
        return arrow.get(value).datetime


class EmailSchema(Schema):
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
    street = fields.String()
    city = fields.String()
    state = fields.String()
    postal_code = fields.String()
    country = fields.String()
