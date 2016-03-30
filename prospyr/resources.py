# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from itertools import count
from logging import getLogger

from marshmallow import Schema
from requests import codes

from prospyr import connection, exceptions, fields, mixins

logger = getLogger(__name__)


class Resource(object):
    def __init__(self, **data):
        errors = self.Meta.schema.validate(data=data)
        if errors:
            raise exceptions.ValidationError(errors)
        self._set_fields(data)

    def __repr__(self):
        classname = type(self).__name__
        friendly = str(self)
        return '<%s: %s>' % (classname, friendly)

    def __str__(self):
        return getattr(self, 'id', '(unsaved)')

    def _get_conn(self, using):
        return connection.get(using)

    def _set_fields(self, data):
        """
        Without validating, write `data` onto the fields of this Resource.
        """
        for field, value in data.items():
            setattr(self, field, value)


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

    def filter(self, **query):
        return Search(manager=self, using=self.using).filter(**query)

    def order_by(self, field):
        return Search(manager=self, using=self.using).order_by(field)


class Search(object):
    """
    Immutable, lazy search results.
    """

    def __init__(self, manager, params=None, order_field=None,
                 order_dir='asc', using='default'):
        self._params = params
        self._order_field = order_field
        self._order_dir = order_dir
        self._manager = manager
        self._resource_cls = manager.resource_cls
        self._using = using
        self._cache = None

    def filter(self, **query):
        if not query:
            raise ValueError('At least one parameter must be added '
                             'before searching')

        if self._params is None:
            new_params = {}
        else:
            new_params = self._params.copy()
        new_params.update(query)
        return Search(params=new_params, using=self._using,
                      manager=self._manager, order_field=self._order_field,
                      order_dir=self._order_dir)

    def order_by(self, field):
        dir = 'asc'
        if field.startswith('-'):
            dir, field = 'desc', field[1:]
        return Search(params=self._params, using=self._using,
                      manager=self._manager, order_dir=dir, order_field=field)

    @property
    def _conn(self):
        return connection.get(self._using)

    @property
    def _url(self):
        path = self._manager.resource_cls.Meta.search_path
        return self._conn.build_absolute_url(path)

    def _fetch(self):
        """
        Return Resource instances by querying ProsperWorks.
        """
        if self._params is None:
            raise ValueError('At least one parameter must be added '
                             'before searching')
        results = []
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
            if not page_data:
                break
            page_results = [self._resource_cls(**data) for data in page_data]
            results.extend(page_results)

            # detect last page of results
            if len(page_data) < query['page_size']:
                break

        return results

    def __iter__(self):
        """
        Iterable search results. May evaluate search.
        """
        if self._cache is None:
            self._cache = self._fetch()
        return iter(self._cache)

    def __repr__(self):
        results = list(self)
        first_10 = [repr(r) for r in results[:10]]
        truncated = len(first_10) != len(self)
        if truncated:
            first_10.append('...')

        return '<{cls} Search: [{results}]>'.format(
            cls=self._resource_cls.__name__,
            results=', '.join(first_10)
        )

    def __len__(self):
        """
        Count of search results. May evaluate search.
        """
        if self._cache is None:
            self._cache = self._fetch()
        return len(self._cache)


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


class CompanySchema(Schema):
    id = fields.Integer()
    name = fields.String(required=True)
    address = fields.Nested(AddressSchema)
    assignee_id = fields.Integer(allow_none=True)
    company_id = fields.Integer(allow_none=True)
    company_name = fields.String()
    contact_type_id = fields.Integer(allow_none=True)
    details = fields.String(allow_none=True)
    emails = fields.Nested(EmailSchema(many=True))
    phone_numbers = fields.Nested(PhoneNumberSchema(many=True))
    socials = fields.Nested(SocialSchema(many=True))
    tags = fields.List(fields.String)
    title = fields.String()
    date_created = fields.Unix()
    date_modified = fields.Unix()
    websites = fields.Nested(CustomFieldSchema(many=True))
    custom_fields = fields.Nested(WebsiteSchema(many=True))


class Company(Resource, mixins.Readable):

    objects = Manager()

    class Meta(object):
        schema = CompanySchema()
        search_path = 'companies/search/'
        detail_path = 'companies/{id}/'

    def __str__(self):
        return self.name
