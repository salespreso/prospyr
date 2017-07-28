# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from logging import getLogger

from marshmallow import fields
from requests import codes
from six import string_types, with_metaclass

from prospyr import connection, exceptions, schema
from prospyr.exceptions import ApiError
from prospyr.managers import ListOnlyManager, Manager
from prospyr.util import encode_typename, import_dotted_path

logger = getLogger(__name__)


class Creatable(object):
    """
    Allows creation of a Resource. Should be mixed in with that class.
    """

    # pworks uses 200 OK for creates. 201 CREATED is here through optimism.
    _create_success_codes = {codes.created, codes.ok}

    def create(self, using='default'):
        """
        Create a new instance of this Resource. True on success.
        """
        if hasattr(self, 'id'):
            raise ValueError(
                '%s cannot be created; it already has an id' % self
            )
        conn = self._get_conn(using)
        path = self.Meta.create_path
        resp = conn.post(conn.build_absolute_url(path), json=self._raw_data)

        if resp.status_code in self._create_success_codes:
            data = self._load_raw(resp.json())
            self._set_fields(data)
            return True
        elif resp.status_code == codes.unprocessable_entity:
            error = resp.json()
            raise ValueError(error['message'])
        else:
            raise ApiError(resp.status_code, resp.text)


class Readable(object):
    """
    Allows reading of a Resource. Should be mixed in with that class.
    """

    _read_success_codes = {codes.ok}

    def read(self, using='default'):
        """
        Read this Resource from remote API. True on success.
        """
        logger.debug('Connected using %s', using)
        path = self._get_path()
        conn = self._get_conn(using)
        resp = conn.get(conn.build_absolute_url(path))
        if resp.status_code not in self._read_success_codes:
            raise ApiError(resp.status_code, resp.text)

        data = self._load_raw(resp.json())
        self._set_fields(data)
        return True

    def _get_path(self):
        if getattr(self, 'id', None) is None:
            raise ValueError('%s must be saved before it is read' % self)
        return self.Meta.detail_path.format(id=self.id)


class Singleton(Readable):
    """
    Allows reading of a Resource without an id.
    Should be mixed in with that class.
    """

    def _get_path(self):
        return self.Meta.detail_path


class Updateable(object):
    """
    Allows updating a Resource. Should be mixed in with that class.
    """

    _update_success_codes = {codes.ok}

    def update(self, using='default'):
        """
        Update this Resource. True on success.
        """
        if getattr(self, 'id', None) is None:
            raise ValueError('%s cannot be deleted before it is saved' % self)

        # can't update IDs
        data = self._raw_data
        data.pop('id')

        conn = self._get_conn(using)
        path = self.Meta.detail_path.format(id=self.id)
        resp = conn.put(conn.build_absolute_url(path), json=data)
        if resp.status_code in self._update_success_codes:
            return True
        elif resp.status_code == codes.unprocessable_entity:
            error = resp.json()
            raise ValueError(error['message'])
        else:
            raise ApiError(resp.status_code, resp.text)


class Deletable(object):
    """
    Allows deletion of a Resource. Should be mixed in with that class.
    """

    _delete_success_codes = {codes.ok}

    def delete(self, using='default'):
        """
        Delete this Resource. True on success.
        """
        if getattr(self, 'id', None) is None:
            raise ValueError('%s cannot be deleted before it is saved' % self)
        conn = self._get_conn(using)
        path = self.Meta.detail_path.format(id=self.id)
        resp = conn.delete(conn.build_absolute_url(path))
        if resp.status_code in self._delete_success_codes:
            return True
        else:
            raise ApiError(resp.status_code, resp.text)


class ReadWritable(Creatable, Readable, Updateable, Deletable):
    pass


class ResourceMeta(type):
    """
    Metaclass of all Resources.

    Pulls marshmallow schema fields onto a Schema definition.
    """
    class Meta(object):
        abstract = True

    def __new__(cls, name, bases, attrs):
        super_new = super(ResourceMeta, cls).__new__

        # only do metaclass tomfoolery for concrete resources.
        subclasses = {b for b in bases if issubclass(b, Resource)}
        requires_schema = any(getattr(s.Meta, 'abstract', True)
                              for s in subclasses)
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
        if 'Meta' not in attrs:
            raise AttributeError('Class %s must define a `class Meta`' %
                                 cls.__name__)
        attrs['Meta'].schema = schema_cls()

        return super_new(cls, name, bases, attrs)


class Resource(with_metaclass(ResourceMeta)):
    """
    Superclass of all ProsperWorks API resources.

    This class should be mixed with mixins.Readable, mixins.Creatable etc.
    """
    objects = Manager()

    class Meta:
        abstract = True

    def __init__(self, **data):
        self._set_fields(data)

    def validate(self):
        schema = self.Meta.schema
        attrs = set(dir(self)) & set(schema.declared_fields)
        data = {k: getattr(self, k) for k in attrs}
        errors = self.Meta.schema.validate(data)
        if errors:
            raise exceptions.ValidationError(
                ('{cls} instance is not valid; Errors encountered: {errors}'
                 .format(cls=type(self), errors=repr(errors))),
                raw_data=data,
                resource_cls=type(self),
                errors=errors
            )

    @classmethod
    def from_api_data(cls, orig_data):
        """
        Alternate constructor. Build instance from ProsperWorks API data.
        """
        data = cls._load_raw(orig_data)
        instance = cls()
        instance._set_fields(data)
        instance._orig_data = orig_data
        return instance

    @classmethod
    def _load_raw(cls, raw_data):
        """
        Convert `raw_data` into a Resource instance.
        """
        data, errors = cls.Meta.schema.load(raw_data)
        if errors:
            raise exceptions.ValidationError(
                ('ProsperWorks delivered data which does not agree with the '
                 'local Prospyr schema for %s. This is probably a Prospyr '
                 'bug. Errors encountered: %s' % (cls.__name__, repr(errors))),
                raw_data=raw_data,
                resource_cls=cls,
                errors=errors,
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
                'Could not serialize %s data: %s' % (self, repr(errors)),
                raw_data=data,
                resource_cls=type(self),
                errors=errors,
            )

        return data


class SecondaryResource(Resource):
    """
    Secondary resources have only a list URL.
    """
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
