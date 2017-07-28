# -*- coding: utf-8 -*-
"""
Resources related to Custom Fields.
"""

from __future__ import absolute_import, print_function, unicode_literals

from operator import attrgetter

from marshmallow import fields
from marshmallow.validate import OneOf, Range

from prospyr import exceptions, schema
from prospyr.fields import Unix, normalise_many
from prospyr.resource_base import (Readable, Related, Resource,
                                   SecondaryResource)


class CustomFieldDefinition(SecondaryResource, Readable):
    """
    Model ProsperWorks' custom field definitions

    https://www.prosperworks.com/developer_api/custom_field_definitions

    Such a definition is in most cases just a field name and a type  (e.g.
    "renewal_date" and "date"). The exceptions are definitions with these
    types:

      - Dropdown, which has one or more nested Options
      - MultiSelect, which has the same
      - Currency, which has a currency like JPY or AUD in addition to a numeric
        value.

    Note that the *values* users enter against these custom fields are not
    stored by these records.
    """

    class Meta:
        list_path = 'custom_field_definitions/'

    id = fields.Integer()
    name = fields.String()
    rank = fields.Integer()
    data_type = fields.String(
        validate=OneOf(choices=('String', 'Text', 'Dropdown', 'Date',
                                'Checkbox', 'MultiSelect', 'Float', 'URL',
                                'Percentage', 'Currency')),
    )
    currency = fields.String()
    options = fields.Nested(schema.OptionSchema, many=True)

    CHOICE_TYPES = {'Dropdown', 'Checkbox', 'MultiSelect'}
    CURRENCY_TYPES = {'Currency'}

    def validate(self):
        return super().validate()

        if self.data_type not in self.CURRENCY_TYPES and self.currency:
            raise exceptions.ValidationError(
                '`currency` field can only be used with `data_type` %s' %
                ', '.join(self.CURRENCY_TYPES)
            )

        if self.data_type not in self.CHOICE_TYPES and self.options:
            raise exceptions.ValidationError(
                '`options` field can only be used with `data_type` %s' %
                ', '.join(self.CHOICE_TYPES)
            )

    @property
    def field_cls(self):
        mapping = {
            'String': String,
            'Text': Text,
            'Date': Date,
            'Dropdown': Dropdown,
            'Checkbox': Checkbox,
            'MultiSelect': MultiSelect,
            'Float': Float,
            'URL': Url,
            'Percentage': Percentage,
            'Currency': Currency,
        }
        cls = mapping.get(self.data_type, Custom)
        return cls

    @property
    def options_by_id(self):
        return {o.id: o for o in self.options}

    @property
    def options_by_name(self):
        return {o.name: o for o in self.options}


class SelectedOption(fields.Field):
    """
    Convert Option.id to Option.

    Parent schema must identify a CustomFieldDefinition at attribute
    `custom_field`.
    """
    def __init__(self, custom_field, *args, **kwargs):
        self.custom_field = custom_field
        self.many = kwargs.get('many', False)
        if not self.custom_field.endswith('_id'):
            self.custom_field = '%s_id' % self.custom_field
        super().__init__(*args, **kwargs)

    @normalise_many
    def _deserialize(self, values, attr, obj):
        defn_id = obj[self.custom_field]
        defn = CustomFieldDefinition.objects.get(defn_id)
        return [defn.options_by_id[v] for v in values]


class CustomFieldList(list):
    """
    Add convenient `.dict` attribute to custom field list
    """

    @property
    def dict(self):
        """
        A convenient dict of custom field names and values.

        While a list of CustomField instances delivers all possible
        information, a name: value dictionary is easier to work with in the
        majority of cases.
        """
        d = {}
        for field in self:
            value = field.value
            if issubclass(type(field), CustomWithOptions):
                try:
                    value = value.name
                except AttributeError:
                    value = sorted(value, key=attrgetter('rank'))
                    value = [v.name for v in value]
            d[field.custom_field_definition.name] = value
        return d


class CustomField(fields.Field):

    def __init__(self, *args, **kwargs):
        self.many = kwargs.get('many', False)
        assert 'load_only' not in kwargs, 'Custom Fields are read-only'
        kwargs['load_only'] = True
        super().__init__(*args, **kwargs)

    @normalise_many
    def _deserialize(self, values, attr, obj):
        deserialised = []
        for value in values:
            cfd_id = value['custom_field_definition_id']
            defn = CustomFieldDefinition.objects.get(id=cfd_id)
            cls = defn.field_cls
            deser = cls.from_api_data(value)
            deserialised.append(deser)
        return CustomFieldList(deserialised)


class Custom(Resource):
    class Meta:
        pass

    @property
    def name(self):
        return self.custom_field_definition.name

    def __str__(self):
        return '{name}={value}'.format(
            name=self.name,
            value=repr(self.value)
        )


class CustomWithOptions(Custom):
    class Meta:
        pass

    def __str__(self):
        try:
            value = self.value.name
        except AttributeError:
            value = self.value
        return '{name}={value}'.format(
            name=self.custom_field_definition.name,
            value=repr(value)
        )


class Date(Custom):
    class Meta:
        pass
    value = Unix(allow_none=True)
    custom_field_definition = Related(CustomFieldDefinition)


class String(Custom):
    class Meta:
        pass
    value = fields.String(allow_none=True)
    custom_field_definition = Related(CustomFieldDefinition)


class Text(Custom):
    class Meta:
        pass
    value = fields.String(allow_none=True)
    custom_field_definition = Related(CustomFieldDefinition)


class Dropdown(CustomWithOptions):
    class Meta:
        pass
    value = SelectedOption(custom_field='custom_field_definition',
                           allow_none=True)
    custom_field_definition = Related(CustomFieldDefinition)


class Checkbox(Custom):
    class Meta:
        pass
    value = fields.Raw(allow_none=True)  # TODO
    custom_field_definition = Related(CustomFieldDefinition)


class MultiSelect(CustomWithOptions):
    class Meta:
        pass
    value = SelectedOption(custom_field='custom_field_definition',
                           many=True)
    custom_field_definition = Related(CustomFieldDefinition)


class Float(Custom):
    class Meta:
        pass
    value = fields.Float(allow_none=True)
    custom_field_definition = Related(CustomFieldDefinition)


class Url(Custom):
    class Meta:
        pass
    value = fields.URL(allow_none=True)
    custom_field_definition = Related(CustomFieldDefinition)


class Percentage(Custom):
    class Meta:
        pass
    value = fields.Float(allow_none=True, validate=Range(0, 100))
    custom_field_definition = Related(CustomFieldDefinition)


class Currency(Custom):
    class Meta:
        pass
    value = fields.Float(allow_none=True)
    custom_field_definition = Related(CustomFieldDefinition)

    @property
    def currency(self):
        return self.custom_field_definition.currency

    def __str__(self):
        return '{name}={currency}{value}'.format(
            name=self.name,
            currency=self.currency if self.value is not None else '',
            value=self.value,
        )
