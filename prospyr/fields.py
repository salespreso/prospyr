# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import arrow
from marshmallow.fields import *  # noqa


class Unix(Field):
    def _serialize(self, value, attr, obj):
        return Arrow(value).timestamp

    def _deserialize(self, value, attr, obj):
        return arrow.get(value).datetime
