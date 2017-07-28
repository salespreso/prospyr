from collections import defaultdict

from requests import codes

from prospyr import connection
from prospyr.exceptions import ApiError, ProspyrException
from prospyr.search import ActivityTypeListSet, ListSet, ResultSet


class Filterable(object):
    def filter(self, **query):
        fresh = self._search_cls(resource_cls=self.resource_cls,
                                 using=self.using)
        return fresh.filter(**query)


class Listable(object):
    def all(self):
        return self.filter()


class Orderable(object):
    def order_by(self, field):
        fresh = self._search_cls(resource_cls=self.resource_cls,
                                 using=self.using)
        return fresh.order_by(field)


class Getable(object):
    def get(self, id):
        instance = self.resource_cls()
        instance.id = id
        instance.read(using=self.using)
        return instance


class BaseManager(object):

    _search_cls = ResultSet

    def __get__(self, instance, cls):
        if instance:
            raise AttributeError(
                'You can\'t access this {manager_cls} from a resource '
                'instance; Use {resource_cls}.objects instead'.format(
                    resource_cls=type(instance).__name__,
                    manager_cls=type(self).__name__
                )
            )
        self.resource_cls = cls
        self.using = 'default'
        return self

    def use(self, name):
        self.using = name
        return self

    def store_invalid(self, dest):
        fresh = self._search_cls(resource_cls=self.resource_cls,
                                 using=self.using)
        return fresh.store_invalid(dest)

    def all(self):
        raise NotImplementedError('%s does not support listing all records'
                                  % type(self).__name__)

    def filter(self, **query):
        raise NotImplementedError('%s does not support filtering records'
                                  % type(self).__name__)

    def order_by(self, field):
        raise NotImplementedError('%s does not support ordering records'
                                  % type(self).__name__)


class Manager(Listable, Filterable, Orderable, Getable, BaseManager):
    """
    Manages a collection of ProsperWorks resources.

    Applies to most available resources.
    """
    pass


class ListOnlyManager(Manager):
    """
    Manage a resource which has only a list URL.

    Some ProsperWorks resources are list-only; they have no search or detail
    URLs. The get() method is simulated. filtering and ordering is disabled.
    """

    _search_cls = ListSet
    _cache = defaultdict(dict)

    def results_by_id(self, force_refresh=False):
        # must key by resource because manager may be shared
        cache = self._cache[self.resource_cls]

        if not cache or force_refresh is True:
            rs = self.all()
            cache.update({r.id: r for r in rs})
        return cache

    def get(self, id):
        result = self.results_by_id().get(id)
        if result is None:
            # perhaps our cache is stale?
            result = self.results_by_id(force_refresh=True).get(id)
            if result is None:
                raise KeyError('Record with id `%s` does not exist' % id)
        return result

    def all(self):
        return self._search_cls(resource_cls=self.resource_cls,
                                using=self.using)


class NoCollectionManager(BaseManager, Getable):
    """
    Manage resources which cannot be listed or searched.
    """


class SingletonManager(NoCollectionManager):
    """
    Manage resources that have a single object.
    """

    def get(self):
        instance = self.resource_cls()
        instance.read(using=self.using)
        return instance


class ActivityTypeManager(ListOnlyManager):
    """
    Special-case ActivityType's listing actually being two seperate lists.
    """
    _search_cls = ActivityTypeListSet


class PersonManager(Manager):
    """
    Special-case get() to allow fetch by email.
    """
    def get(self, id=None, email=None):
        if id is not None:
            return super(PersonManager, self).get(id)
        elif email is not None:
            conn = connection.get(self.using)
            path = self.resource_cls.Meta.fetch_by_email_path
            resp = conn.post(
                conn.build_absolute_url(path),
                json={'email': email}
            )
            if resp.status_code not in {codes.ok}:
                raise ApiError(resp.status_code, resp.text)
            return self.resource_cls.from_api_data(resp.json())
        raise ProspyrException("id or email is required when getting a Person")
