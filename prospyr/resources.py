# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

import sys
from logging import getLogger

from marshmallow import fields, validate
from six import string_types, with_metaclass

from prospyr import connection, exceptions, mixins, schema
from prospyr.fields import NestedResource, Unix
from prospyr.search import ListSet, ResultSet
from prospyr.util import import_dotted_path

logger = getLogger(__name__)


def encode_typename(name):
    """
    Type names must be bytes in Python 2, unicode in Python 3
    """
    if sys.version_info < (3, 0, 0):
        return name.encode('ascii')
    return name


class Manager(object):

    def get(self, id):
        instance = self.resource_cls()
        instance.id = id
        instance.read(using=self.using)
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
        return ResultSet(resource_cls=self.resource_cls,
                         using=self.using).filter(**query)

    def order_by(self, field):
        return ResultSet(resource_cls=self.resource_cls,
                         using=self.using).order_by(field)


class ListOnlyManager(Manager):

    _results_by_id = None

    def results_by_id(self, force_refresh=False):
        if self._results_by_id is None or force_refresh is True:
            rs = self.all()
            self._results_by_id = {r.id: r for r in rs}
        return self._results_by_id

    def get(self, id):
        result = self.results_by_id().get(id)
        if result is None:
            result = self.results_by_id(force_refresh=True).get(id)
            if result is None:
                raise KeyError('Record with id `%s` does not exist' % id)
        return result

    def all(self):
        return ListSet(resource_cls=self.resource_cls, using=self.using)


class ResourceMeta(type):
    """
    Metaclass of all Resources.
    """
    class Meta(object):
        abstract = True

    def __new__(cls, name, bases, attrs):
        super_new = super(ResourceMeta, cls).__new__

        # only do metaclass tomfoolery for resource *subclasses*
        #  parents = []
        #  for base in bases:
            #  if hasattr(base, 'Meta') and getattr(base.Meta, 'abstract')
        #  parents = [b for b in bases if issubclass(b, Resource)]
        #  if not parents:
        subclasses = {b for b in bases if issubclass(b, Resource)}
        #  subclasses = subclasses - {Resource, SecondaryResource}
        requires_schema = any(getattr(s.Meta, 'abstract', True) for s in subclasses)
        if not requires_schema:
            return super_new(cls, name, bases, attrs)

        # move marshmallow fields to a new Schema subclass on cls.Meta
        schema_attrs = {}
        for attr, value in list(attrs.items()):
            if isinstance(value, fields.Field):
                schema_attrs[attr] = attrs.pop(attr)
            elif hasattr(value, 'modify_schema_attrs'):
                schema_attrs = value.modify_schema_attrs(attr, schema_attrs)
        schema_cls = type(
            encode_typename('%sSchema' % name),
            (schema.TrimSchema, ),
            schema_attrs
        )
        attrs['Meta'].schema = schema_cls()

        return super_new(cls, name, bases, attrs)


class Resource(with_metaclass(ResourceMeta)):

    objects = Manager()

    class meta:
        abstract = True

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
        data = cls._load_raw(data)
        instance = cls()
        instance._set_fields(data)
        return instance

    @classmethod
    def _load_raw(cls, raw_data):
        data, errors = cls.Meta.schema.load(raw_data)
        if errors:
            raise exceptions.ValidationError(
                'ProsperWorks delivered data which does not agree with the '
                'local Prospyr schema. This is probably a Prospyr bug. '
                'Errors encountered: %s' % repr(errors)
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
        data, errors = schema.dump(self)
        if errors:
            raise exceptions.ValidationError(
                'Could not serialize %s data: %s' % (self, repr(errors))
            )

        return data


class SecondaryResource(Resource):

    class Meta:
        abstract = True

    objects = ListOnlyManager()


class Related(object):
    """
    Behave as a related object when an attribute of a Resource.
    """

    def __init__(self, related_cls, required=False):
        self._related_cls = related_cls
        self.required = required

    @property
    def related_cls(self):
        if isinstance(self._related_cls, string_types):
            self._related_cls = import_dotted_path(self._related_cls)
        return self._related_cls

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

    def modify_schema_attrs(self, self_attr, schema_attrs):
        allow_none = (self.required is False)
        field = fields.Integer(allow_none=allow_none)
        schema_attrs['%s_id' % self_attr] = field
        return schema_attrs


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
    address = fields.Nested(schema.AddressSchema, allow_none=True)
    assignee_id = fields.Integer(allow_none=True)
    assignee = Related(User)
    contact_type_id = fields.Integer(allow_none=True)
    details = fields.String(allow_none=True)
    email_domain = fields.String(allow_none=True)
    phone_numbers = fields.Nested(schema.PhoneNumberSchema(many=True))
    socials = fields.Nested(schema.SocialSchema(many=True))
    tags = fields.List(fields.String)
    date_created = Unix()
    date_modified = Unix()
    websites = fields.Nested(schema.CustomFieldSchema(many=True))
    custom_fields = fields.Nested(schema.WebsiteSchema(many=True))


class Person(Resource, mixins.ReadWritable):

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
    date_created = Unix()
    date_modified = Unix()
    websites = fields.Nested(schema.CustomFieldSchema, many=True)
    custom_fields = fields.Nested(schema.WebsiteSchema, many=True)


class LossReason(SecondaryResource, mixins.Readable):
    class Meta(object):
        list_path = 'loss_reasons'

    id = fields.Integer()
    name = fields.String(required=True)


class PipelineStage(SecondaryResource, mixins.Readable):
    class Meta(object):
        list_path = 'pipeline_stages'

    id = fields.Integer()
    name = fields.String(required=True)
    pipeline = Related('prospyr.resources.Pipeline')


class Pipeline(SecondaryResource, mixins.Readable):
    class Meta(object):
        list_path = 'pipelines'

    id = fields.Integer()
    name = fields.String(required=True)
    stages = NestedResource(
        PipelineStage,
        many=True,
    )


class CustomerSource(SecondaryResource, mixins.Readable):
    class Meta(object):
        list_path = 'customer_sources'

    id = fields.Integer()
    name = fields.String(required=True)


class Opportunity(Resource, mixins.ReadWritable):
    class Meta(object):
        create_path = 'opportunities/'
        search_path = 'opportunities/search/'
        detail_path = 'opportunities/{id}/'
        order_fields = {
            'name',
            'assignee',
            'company_name',
            'customer_source_id',
            'monetary_value',
            'primary_contact',
            'priority',
            'status',
            'inactive_days',
            'last_interaction',
            'interaction_count',
            'date_created',
            'date_modified',
        }

    id = fields.Integer()
    name = fields.String(required=True)
    company_name = fields.String(allow_none=True, load_only=True)
    close_date = Unix()
    details = fields.String(allow_none=True)
    monetary_value = fields.Integer(allow_none=True)

    assignee = Related(User)
    company = Related(Company)
    loss_reason = Related(LossReason)
    customer_source = Related(CustomerSource)
    pipeline = Related(Pipeline)
    pipeline_stage = Related(PipelineStage)
    primary_contact = Related(Person, required=True)
    priority = fields.String(
        allow_none=True,
        validate=validate.OneOf(choices=('None', 'Low', 'Medium', 'High')),
    )
    stage = fields.String(
        allow_none=True,
        validate=validate.OneOf(choices=('Open', 'Won', 'Lost', 'Abandoned')),
    )
    tags = fields.List(fields.String)
    win_probability = fields.Integer()
    date_created = Unix()
    date_modified = Unix()
