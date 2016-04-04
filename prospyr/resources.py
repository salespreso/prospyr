# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from logging import getLogger

from marshmallow import fields
from six import with_metaclass

from prospyr import connection, exceptions, mixins, schema
from prospyr.search import ResultSet

logger = getLogger(__name__)


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
        data, errors = schema.dump(self)
        if errors:
            raise exceptions.ValidationError(
                'Could not serialize %s data: %s' % (self, repr(errors))
            )

        return data


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
    address = fields.Nested(schema.AddressSchema, allow_none=True)
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
