from nose.tools import assert_raises

from prospyr.managers import NoCollectionManager
from tests import reset_conns


class FakeResource(object):
    objects = NoCollectionManager()


@reset_conns
def test_not_a_collection_manager():
    mgr = FakeResource.objects

    with assert_raises(NotImplementedError):
        mgr.all()

    with assert_raises(NotImplementedError):
        mgr.order_by('foo')

    with assert_raises(NotImplementedError):
        mgr.filter(foo='bar')
