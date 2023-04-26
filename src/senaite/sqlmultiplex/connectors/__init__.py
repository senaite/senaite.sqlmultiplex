# -*- coding: utf-8 -*-
import json

from senaite.core.supermodel import SuperModel
from senaite.sqlmultiplex import PRODUCT_NAME
from senaite.sqlmultiplex import utils
from six import string_types
from bika.lims import api


class SqlConnector(object):

    connector_id = None
    column_uid = "uid"
    create_table_template = ""
    column_definition_template = ""
    insert_update_template = ""
    delete_template = "DELETE FROM {table_name} WHERE {column_uid}='{uid}'"
    unquoted_types = []

    @property
    def host(self):
        key = "{}.host".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def port(self):
        key = "{}.port".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def dbname(self):
        key = "{}.database".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def username(self):
        key = "{}.user".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def password(self):
        key = "{}.password".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def raise_errors(self):
        """Returns whether an exception must be raised and transaction aborted
        when SQL errors occur
        """
        reg_id = "{}.raise_errors".format(PRODUCT_NAME)
        return api.get_registry_record(reg_id)

    def get_table_name(self, obj):
        return api.get_portal_type(obj).lower()

    def get_column_name(self, obj, field):
        """Returns the name of the column for the given field
        """
        if isinstance(field, string_types):
            field_name = field
        else:
            field_name = field.getName()
        return field_name.lower()

    def get_column_info(self, obj, field):
        return {
            "name": self.get_column_name(obj, field),
            "type": self.get_column_type(obj, field),
            "constraint": "",
        }

    def get_column_definition(self, obj, field):
        column_info = self.get_column_info(obj, field)
        return self.column_definition_template.format(**column_info).strip()

    def get_create_table_statement(self, obj):
        fields = utils.get_supported_fields(obj)
        columns = [self.get_column_definition(obj, field) for field in fields]
        params = {
            "column_uid": self.column_uid,
            "table_name": self.get_table_name(obj),
            "columns_create": ", ".join(columns),
        }
        return self.create_table_template.format(**params)

    def get_column_type(self, obj, field):
        raise NotImplementedError()

    def with_quotes(self, field):
        return

    def is_reference_field(self, field):
        return field.getType().find("Reference") > -1

    def is_string_field(self, field):
        return field.type == "string"

    def is_boolean_field(self, field):
        return field.type == "boolean"

    def is_fixed_point_field(self, field):
        return field.type == "fixedpoint"

    def is_duration_field(self, field):
        return field.type == "duration"

    def is_integer_field(self, field):
        return field.type == "integer"

    def get_column_value(self, obj, field):
        # resolve the value for the given field or attr/function name
        if isinstance(field, string_types):
            attr = getattr(obj, "get{}".format(field), None)
            if not callable(attr):
                attr = getattr(obj, field, None)
            value = attr() if callable(attr) else attr
        elif self.is_reference_field(field):
            value = field.getRaw(obj)
        else:
            value = field.get(obj)

        # Sanitize to hold values suitable for SQL
        sm = SuperModel(obj)
        if api.is_object(value):
            value = api.get_uid(value)
        elif isinstance(value, (list, tuple, dict)):
            if not value:
                value = None
            else:
                value = sm.stringify(value)
                value = json.dumps(value)

        # Quote/unquote values for the SQL statement
        if self.get_column_type(obj, field) not in self.unquoted_types:
            if value is not None:
                value = sm.stringify(value)

        return value

    def get_info(self, obj):
        """Returns a dict with the information of the object, suitable for SQL
        operations
        """
        info = {}
        # Generate a dict with the requested attributes only
        for field in utils.get_supported_fields(obj):
            column_name = self.get_column_name(obj, field)
            info[column_name] = self.get_column_value(obj, field)

        # Always include the UID
        info[self.column_uid] = api.get_uid(obj)
        return info

    def insert_or_update(self, obj):
        """Inserts or updates the given object with the given attributes to
        the database
        """
        raise NotImplementedError()

    def delete(self, obj):
        """Deletes the object passed-in from the database
        """
        params = {
            "table_name": self.get_table_name(obj),
            "column_uid": self.column_uid,
            "uid": api.get_uid(obj),
        }
        statement = self.delete_template.format(**params)
        self.execute(statement, raise_error=self.raise_errors)

    def execute(self, operation, params=None, raise_error=True):
        raise NotImplementedError()
