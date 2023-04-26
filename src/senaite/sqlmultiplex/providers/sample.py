from senaite.sqlmultiplex.providers import SQLATContentInfo
from bika.lims.interfaces import IAnalysisRequest
from zope.component import adapter


@adapter(IAnalysisRequest)
class PSQLAnalysisRequestContentInfo(SQLATContentInfo):
    """"Generic SQL adapter for Archetypes
    """

    def get_column_type(self, obj, field):
        # TODO We just always assume a varchar type here!

        return "varchar (255)"

    def get_create_table_statement(self):
        """returns the SQL script for the creation of the table for objects
        from this same type
        """
        table_name = self.get_table_name()
        statement = "CREATE TABLE {} (" \
                    "UID char(32) CONSTRAINT {}_uid_key PRIMARY KEY, " \
                    "{})"


        for field in self.get_fields():
            col_name = field.getName()

            col_def = "{} varchar"
        cols = ", ".join(map())
        for field in self.get_fields():

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

