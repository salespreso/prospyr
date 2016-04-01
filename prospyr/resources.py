# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from itertools import count, islice, tee
from logging import getLogger

from marshmallow import Schema, fields
from requests import codes
from six import with_metaclass

from prospyr import connection, exceptions, mixins, schema

logger = getLogger(__name__)


class Manager(object):

    def get(self, id, using='default'):
        instance = self.resource_cls()
        instance.id = id
        instance.read(using=using)
        return instance

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

    def all(self):
        return self.filter()

    def filter(self, **query):
        return Search(manager=self, using=self.using).filter(**query)

    def order_by(self, field):
        return Search(manager=self, using=self.using).order_by(field)


class ResourceMeta(type):
    """
    Metaclass of all Resources.
    """
    def __new__(cls, name, bases, attrs):
        super_new = super(ResourceMeta, cls).__new__

        # only do metaclass tomfoolery for resource *subclasses*
        parents = [b for b in bases if issubclass(b, Resource)]
        if not parents:
            return super_new(cls, name, bases, attrs)

        # move marshmallow fields to a new Schema subclass on cls.Meta
        schema_attrs = {}
        for attr, value in list(attrs.items()):
            if isinstance(value, fields.Field):
                schema_attrs[attr] = attrs.pop(attr)
        schema_cls = type(
            '%sSchema' % name,
            (schema.TrimSchema, ),
            schema_attrs
        )
        attrs['Meta'].schema = schema_cls()

        return super_new(cls, name, bases, attrs)


class Resource(with_metaclass(ResourceMeta)):

    objects = Manager()

    def __init__(self, **data):
        self._set_fields(data)

    def validate(self):
        schema = self.Meta.schema
        attrs = set(dir(self)) & set(schema.declared_fields)
        data = {k: getattr(self, k) for k in attrs}
        errors = self.Meta.schema.validate(data)
        if errors:
            raise exceptions.ValidationError(errors)

    @classmethod
    def from_api_data(cls, data):
        """
        Alternate constructor. Build instance from ProsperWorks API data.
        """
        data, errors = cls.Meta.schema.load(data)
        if errors:
            raise exceptions.ValidationError(
                'ProsperWorks delivered data which does not agree with the '
                'local prospyr schema. Errors encountered: %s' % repr(errors)
            )
        instance = cls()
        instance._set_fields(data)
        return instance

    def _data_from_resp(self, resp):
        data, errors = self.Meta.schema.load(resp.json())
        if errors:
            raise exceptions.ValidationError(
                'ProsperWorks delivered data which does not agree with the '
                'local prospyr schema. Errors encountered: %s' % repr(errors)
            )
        return data

    def __repr__(self):
        classname = type(self).__name__
        friendly = str(self)
        return '<%s: %s>' % (classname, friendly)

    def __str__(self):
        if hasattr(self, 'name'):
            return self.name
        elif hasattr(self, 'id'):
            return str(self.id)
        return '(unsaved)'

    def _get_conn(self, using):
        return connection.get(using)

    def _set_fields(self, data):
        """
        Without validating, write `data` onto the fields of this Resource.
        """
        for field, value in data.items():
            setattr(self, field, value)

    @property
    def _raw_data(self):
        schema = self.Meta.schema
        cleaned = {k: getattr(self, k) for k in schema.declared_fields
                   if hasattr(self, k)}
        data, errors = schema.dump(cleaned)
        if errors:
            raise exceptions.ValidationError(
                'Could not serialize %s data: %s' % (self, repr(errors))
            )

        return data


class Search(object):
    """
    Immutable, lazy search results.
    """

    def __init__(self, manager, params=None, order_field=None,
                 order_dir='asc', using='default'):
        self._params = params or {}
        self._order_field = order_field
        self._order_dir = order_dir
        self._manager = manager
        self._resource_cls = manager.resource_cls
        self._using = using
        self._results = self._results_generator()

    def all(self):
        return self.filter()

    def filter(self, **query):
        new_params = self._params.copy()
        new_params.update(query)
        return Search(params=new_params, using=self._using,
                      manager=self._manager, order_field=self._order_field,
                      order_dir=self._order_dir)

    def order_by(self, field):
        dir = 'asc'
        if field.startswith('-'):
            dir, field = 'desc', field[1:]
        available = self._resource_cls.Meta.order_fields
        if field not in available:
            raise ValueError(
                'Cannot sort by `{field}`; try one of {valid}'
                .format(field=field, valid=', '.join(sorted(available)))
            )
        return Search(params=self._params, using=self._using,
                      manager=self._manager, order_dir=dir, order_field=field)

    @property
    def _conn(self):
        return connection.get(self._using)

    @property
    def _url(self):
        path = self._manager.resource_cls.Meta.search_path
        return self._conn.build_absolute_url(path)

    def _results_generator(self):
        """
        Return Resource instances by querying ProsperWorks.

        You should not normally need to use this method.
        """
        query = self._params.copy()
        query['page_size'] = 100

        if self._order_field:
            query['sort_by'] = self._order_field
            query['sort_direction'] = self._order_dir

        for query['page_number'] in count(1):
            resp = self._conn.post(self._url, json=query)
            if resp.status_code != codes.ok:
                raise exceptions.ApiError(resp.status_code, resp.text)

            # no (more) results
            page_data = resp.json()
            logger.debug('%s results on page %s of %s',
                         len(page_data), query['page_number'], self._url)
            if not page_data:
                break

            for data in page_data:
                yield self._resource_cls.from_api_data(data)

            # detect last page of results
            if len(page_data) < query['page_size']:
                break

    def __iter__(self):
        """
        All resource instances matching this search. Results are cached.

        Depending on page size, this could result in many requests.
        """
        self._results, cpy = tee(self._results)
        return cpy

    def __getitem__(self, index):
        """
        Fetch the nth of sliceth item from cache or ProsperWorks.

        Fetching item N involves fetching items 0 through N-1. Depending on
        page size and N, this could be many requests.
        """
        self._results, cpy = tee(self._results)
        if type(index) is slice:
            return list(islice(cpy, index.start, index.stop, index.step))
        else:
            try:
                return next(islice(cpy, index, index+1))
            except StopIteration:
                raise IndexError('Search index out of range')

    def __repr__(self):
        # show up to 5 results, then elipses. 6 results are fetched to
        # accomodate the elipses logic.
        first_6 = [str(r) for r in self[:6]]
        truncated = len(first_6) == 6
        if truncated:
            first_6.append('...')

        return '<{cls} Search: [{results}]>'.format(
            cls=self._resource_cls.__name__,
            results=', '.join(first_6)
        )


class Related(object):
    """
    Behave as a related object when an attribute of a Resource.
    """

    def __init__(self, related_cls):
        self.related_cls = related_cls

    def __get__(self, instance, cls):
        if instance is None:
            return self
        attr = self.find_parent_attr(type(instance))
        id = getattr(instance, '%s_id' % attr)
        if id is None:
            return None
        return self.related_cls.objects.get(id=id)

    def __set__(self, instance, value):
        attr = self.find_parent_attr(type(instance))
        if not isinstance(value, self.related_cls):
            raise ValueError(
                '`{value}` must be an instance of `{cls}`'
                .format(value=value, cls=self.related_cls)
            )
        if not value.id:
            raise ValueError(
                '`{value}` can\'t be assigned without an `id` attribute.'
                .format(value=value)
            )
        setattr(instance, '%s_id' % attr, value.id)

    def find_parent_attr(self, parent_cls):
        for attr in dir(parent_cls):
            if getattr(parent_cls, attr) is self:
                return attr
        else:
            raise AttributeError('Cannot find self')


class User(Resource, mixins.Readable):

    id = fields.Integer()
    name = fields.String(required=True)
    email = fields.Email(required=True)

    class Meta(object):
        # schema = schema.UserSchema()
        search_path = 'users/search/'
        detail_path = 'users/{id}/'

    def __str__(self):
        return '{self.name} ({self.email})'.format(self=self)


class Company(Resource, mixins.Readable):

    class Meta(object):
        search_path = 'companies/search/'
        detail_path = 'companies/{id}/'
        order_fields = {
            'name',
            'city',
            'state',
            'assignee',
            'inactive_days',
            'last_interaction',
            'interaction_count',
            'date_created',
            'date_modified',
        }

    id = fields.Integer()
    name = fields.String(required=True)
    address = fields.Nested(schema.AddressSchema)
    assignee_id = fields.Integer(allow_none=True)
    assignee = Related(User)
    contact_type_id = fields.Integer(allow_none=True)
    details = fields.String(allow_none=True)
    email_domain = fields.String(allow_none=True)
    phone_numbers = fields.Nested(schema.PhoneNumberSchema(many=True))
    socials = fields.Nested(schema.SocialSchema(many=True))
    tags = fields.List(fields.String)
    date_created = schema.Unix()
    date_modified = schema.Unix()
    websites = fields.Nested(schema.CustomFieldSchema(many=True))
    custom_fields = fields.Nested(schema.WebsiteSchema(many=True))


class Person(Resource, mixins.Creatable, mixins.Readable, mixins.Deletable,
             mixins.Updateable):

    class Meta(object):
        create_path = 'people/'
        search_path = 'people/search/'
        detail_path = 'people/{id}/'
        order_fields = {
            'name',
            'city',
            'state',
            'assignee',
            'inactive_days',
            'last_interaction',
            'interaction_count',
            'date_created',
            'date_modified',
        }

    id = fields.Integer()
    name = fields.String(required=True)
    address = fields.Nested(
        schema.AddressSchema,
        allow_none=True
    )
    assignee_id = fields.Integer(allow_none=True)
    assignee = Related(User)
    company_id = fields.Integer(allow_none=True)
    company = Related(Company)
    company_name = fields.String(allow_none=True, load_only=True)
    contact_type_id = fields.Integer(allow_none=True)
    details = fields.String(allow_none=True)
    emails = fields.Nested(
        schema.EmailSchema,
        many=True,
        required=True,
    )
    phone_numbers = fields.Nested(schema.PhoneNumberSchema, many=True)
    socials = fields.Nested(schema.SocialSchema, many=True)
    tags = fields.List(fields.String)
    title = fields.String(allow_none=True)
    date_created = schema.Unix()
    date_modified = schema.Unix()
    websites = fields.Nested(schema.CustomFieldSchema, many=True)
    custom_fields = fields.Nested(schema.WebsiteSchema, many=True)
