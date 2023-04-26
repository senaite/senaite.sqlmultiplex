from Products.ATContentTypes.interfaces import IATContentType
from senaite.sqlmultiplex.config import NON_SUPPORTED_FIELD_NAMES
from senaite.sqlmultiplex.config import NON_SUPPORTED_FIELD_TYPES
from senaite.sqlmultiplex.interfaces import ISQLContentInfo
from zope.component import adapter
from zope.interface import implementer

from bika.lims import api


@implementer(ISQLContentInfo)
class SQLContentInfo(object):

    def __init__(self, context):
        self.context = context

    def get_table_name(self):
        """Returns the name of the SQL table to store this content
        """
        return api.get_portal_type(self.context)

    def get_fields(self):
        """Return ISQLFieldInfo objects for this content
        """
        fields = []
        obj_fields = api.get_fields(self.context).values()
        for field in obj_fields:
            # skip fields non-supported fields
            if field.getName() in NON_SUPPORTED_FIELD_NAMES:
                continue
            if field.type in NON_SUPPORTED_FIELD_TYPES:
                continue
            fields.append(field)
        return fields

    def get_columns(self):
        """Return the names of the SQL columns for this content
        """
        return [field.getName() for field in self.get_fields()]


@adapter(IATContentType)
class SQLATContentInfo(SQLContentInfo):
    """"Generic SQL adapter for Archetypes
    """

    def get_create_table_statement(self):
        """returns the SQL script for the creation of the table for objects
        from this same type
        """
        return ""

    def get_update_statement(self):
        """Returns the SQL statement for the update of current object
        """
        return ""

    def get_insert_statement(self, fallback_update=True):
        """Returns the SQL statement for the insert of current object. If
        fallback_update is set to True, the update on primary key conflict is
        also included in the statement
        """
        return ""

    def get_delete_statement(self):
        """Returns the SQL statement for the deletion of current object
        """
        return ""
