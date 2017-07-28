# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, unicode_literals

from logging import getLogger

from marshmallow import fields
from marshmallow.validate import OneOf

from prospyr import custom, managers, schema
from prospyr.fields import NestedIdentifiedResource, NestedResource, Unix
from prospyr.resource_base import (Readable, ReadWritable, Related, Resource,
                                   SecondaryResource, Singleton)
from prospyr.util import to_snake

logger = getLogger(__name__)


class User(Resource, Readable):

    class Meta(object):
        list_path = 'users/'
        detail_path = 'users/{id}/'

    objects = managers.ListOnlyManager()

    id = fields.Integer()
    name = fields.String(required=True)
    email = fields.Email(required=True)

    def __str__(self):
        return '{self.name} ({self.email})'.format(self=self)


class Company(Resource, ReadWritable):

    class Meta(object):
        create_path = 'companies/'
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
    phone_numbers = fields.Nested(schema.PhoneNumberSchema, many=True)
    socials = fields.Nested(schema.SocialSchema, many=True)
    tags = fields.List(fields.String)
    date_created = Unix()
    date_modified = Unix()
    custom_fields = custom.CustomField(many=True)
    websites = fields.Nested(schema.WebsiteSchema, many=True)


class Person(Resource, ReadWritable):

    class Meta(object):
        create_path = 'people/'
        search_path = 'people/search/'
        detail_path = 'people/{id}/'
        fetch_by_email_path = 'people/fetch_by_email/'
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

    objects = managers.PersonManager()

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
    websites = fields.Nested(schema.WebsiteSchema, many=True)
    custom_fields = custom.CustomField(many=True)


class LossReason(SecondaryResource, Readable):
    class Meta(object):
        list_path = 'loss_reasons'

    id = fields.Integer()
    name = fields.String(required=True)


class PipelineStage(SecondaryResource, Readable):
    class Meta(object):
        list_path = 'pipeline_stages'

    id = fields.Integer()
    name = fields.String(required=True)
    pipeline = Related('prospyr.resources.Pipeline')


class Pipeline(SecondaryResource, Readable):
    class Meta(object):
        list_path = 'pipelines'

    id = fields.Integer()
    name = fields.String(required=True)
    stages = NestedResource(
        PipelineStage,
        many=True,
    )


class CustomerSource(SecondaryResource, Readable):
    class Meta(object):
        list_path = 'customer_sources'

    id = fields.Integer()
    name = fields.String(required=True)


class Opportunity(Resource, ReadWritable):
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
    close_date = Unix(allow_none=True)
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
        validate=OneOf(choices=('None', 'Low', 'Medium', 'High')),
    )
    stage = fields.String(
        allow_none=True,
        validate=OneOf(choices=('Open', 'Won', 'Lost', 'Abandoned')),
    )
    tags = fields.List(fields.String)
    win_probability = fields.Integer()
    date_created = Unix()
    date_modified = Unix()
    custom_fields = custom.CustomField(many=True)


class ActivityType(SecondaryResource, Readable):
    class Meta(object):
        list_path = 'activity_types'

    objects = managers.ActivityTypeManager()

    id = fields.Integer(required=True)
    category = fields.String(
        validate=OneOf(choices=('user', 'system')),
    )
    name = fields.String()
    is_disabled = fields.Boolean()
    count_as_interaction = fields.Boolean()


class Identifier(SecondaryResource):

    class Meta:
        pass

    valid_types = {'lead', 'person', 'opportunity', 'company'}
    objects = managers.NoCollectionManager()

    id = fields.Integer()
    type = fields.String(
        validate=OneOf(choices=valid_types)
    )

    @classmethod
    def from_instance(cls, resource):
        if not isinstance(resource, Resource):
            raise ValueError('%s must be an instance of Resource' % resource)
        type_ = to_snake(type(resource).__name__)
        if type_ not in cls.valid_types:
            raise ValueError('%s must be one of %s' % (type_, cls.valid_types))
        return cls(
            type=type_,
            id=resource.id
        )

    @classmethod
    def from_resource_and_id(cls, resource, id):
        type_ = to_snake(resource.__name__)
        if type_ not in cls.valid_types:
            raise ValueError('%s must be one of %s' % (type_, cls.valid_types))
        return cls(type=type_, id=id)

    def __str__(self):
        return '{type} {id}'.format(
            type=self.type.title(),
            id=self.id
        )


class Activity(Resource, ReadWritable):
    class Meta:
        create_path = 'activities/'
        search_path = 'activities/search/'
        detail_path = 'activities/{id}/'
        order_fields = set()  # no ordering

    id = fields.Integer()
    type = NestedResource(ActivityType, id_only=True)
    parent = NestedIdentifiedResource()
    details = fields.String(allow_none=True)
    user = Related(User)
    activity_date = Unix()

    def __str__(self):
        if self._orig_data.get('is_deleted', False):
            return 'Deleted activity'
        else:
            date = getattr(self, 'activity_date', 'unknown date')
            return '%s on %s' % (self.type.name, date)


class Task(Resource, ReadWritable):
    class Meta:
        create_path = 'tasks/'
        search_path = 'tasks/search/'
        detail_path = 'tasks/{id}/'
        order_fields = {
            'name',
            'assigned_to',
            'related_to',
            'status',
            'priority',
            'due_date',
            'reminder_date',
            'completed_date',
            'date_created',
            'date_modified',
        }

    id = fields.Integer()
    name = fields.String()
    related_resource = NestedIdentifiedResource(allow_none=True)
    assignee = Related(User)
    due_date = Unix(allow_none=True)
    reminder_date = Unix(allow_none=True)
    completed_date = Unix(allow_none=True)
    priority = fields.String(validate=OneOf(choices=('None', 'High')))
    status = fields.String(validate=OneOf(choices=('Open', 'Completed')))
    details = fields.String(allow_none=True)
    tags = fields.List(fields.String)
    date_created = Unix()
    date_modified = Unix()
    custom_fields = custom.CustomField(many=True)


class Lead(Resource, ReadWritable):
    class Meta:
        create_path = 'leads/'
        search_path = 'leads/search'
        detail_path = 'leads/{id}'
        order_fields = {
            'name',
            'assignee',
            'company_name',
            'customer_source',
            'monetary_value',
            'status',
            'title',
            'city',
            'state',
            'inactive_days',
            'last_interaction',
            'interaction_count',
            'date_created',
            'date_modified'
        }

    id = fields.Integer()
    name = fields.String()
    address = fields.Nested(schema.AddressSchema, allow_none=True)
    assignee_id = fields.Integer(allow_none=True)
    assignee = Related(User)
    company_name = fields.String(allow_none=True)
    customer_source_id = fields.Integer(allow_none=True)
    customer_source = Related(CustomerSource)
    details = fields.String(allow_none=True)
    email = fields.Nested(schema.EmailSchema, allow_none=True)
    monetary_value = fields.Integer(allow_none=True)
    phone_numbers = fields.Nested(schema.PhoneNumberSchema, many=True)
    socials = fields.Nested(schema.SocialSchema, many=True)
    status = fields.String()
    tags = fields.List(fields.String)
    title = fields.String(allow_none=True)
    websites = fields.Nested(schema.WebsiteSchema, many=True)
    custom_fields = custom.CustomField(many=True)
    date_created = Unix()
    date_modified = Unix()


class Account(Resource, Singleton):

    objects = managers.SingletonManager()

    class Meta:
        detail_path = 'account/'

    id = fields.Integer()
    name = fields.String()


class Placeholder(object):
    """
    Stand-in for Prosperworks resources that Prospyr does not yet model.

    This is required because an Identifier field can point at resources that
    aren't yet implemented.
    """

    def __init__(self, id):
        self.id = id

    def __repr__(self):
        classname = type(self).__name__
        friendly = str(self)
        return '<%s: %s (placeholder)>' % (classname, friendly)

    def __str__(self):
        return str(self.id)


class Project(Placeholder):
    pass
