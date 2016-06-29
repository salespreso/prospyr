# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals


class ProspyrException(Exception):
    pass


class ApiError(ProspyrException):
    def __str__(self):
        return 'HTTP %s: %s' % self.args

    def __unicode__(self):
        return 'HTTP %s: %s' % self.args


class MisconfiguredError(ProspyrException):
    pass


class ValidationError(ProspyrException):
    def __init__(self, message, errors, raw_data, resource_cls):
        super(ValidationError, self).__init__(message)
        self.errors = errors
        self.raw_data = raw_data
        self.resource_cls = resource_cls
