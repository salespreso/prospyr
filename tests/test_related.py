# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from collections import namedtuple

import mock

from prospyr.resources import Related

IdObject = namedtuple('IdObject', 'id')


class Parent(object):
    related = Related(related_cls=mock.Mock())

    def __init__(self, related_id=1):
        self.related_id = related_id


def test_descriptor_get():
    par = Parent()

    par.related  # trigger __get__
    Parent.related.related_cls.objects.get.assert_any_call(id=1)

    assert Parent(related_id=None).related is None


def test_descriptor_set():
    par = Parent()
    Parent.related._related_cls = IdObject
    par.related = IdObject(id=10)
    assert par.related_id == 10
