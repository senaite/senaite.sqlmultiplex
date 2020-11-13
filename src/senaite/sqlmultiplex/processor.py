
import mysql.connector
from bika.lims import api
from Products.CMFCore.interfaces import IPortalCatalogQueueProcessor
from senaite.jsonapi import api as japi
from senaite.sqlmultiplex import logger
from zope.interface import implementer

from senaite.sqlmultiplex import check_installed

TYPES_TO_MULTIPLEX = (
    ("AnalysisRequest", [
        "ClientSampleID",
        "ContactEmail",
        "ContactFullName",
        "ContactUsername",
        "CreatorFullName",
        "DateOfBirth",
        "DateSampled",
        "DateReceived",
        "DatePublished",
        "Gender",
        "Priority",
        "ProfilesTitleStr",
        "SampleTypeTitle",
        "TemplateTitle",
        "created",
        "creation_date",
        "id",
        "modified",
        "parent_id",
        "path",
        "title"
    ]),
)


@implementer(IPortalCatalogQueueProcessor)
class CatalogMultiplexProcessor(object):
    """A catalog multiplex processor
    """

    _connection = None
    _cursor = None
    _config = None

    @property
    def mysql_connection(self):
        """Returns the connection to the destination database
        """
        if self._connection is None:
            config = self.get_connection_configuration()
            self._connection = mysql.connector.connect(**config)
        return self._connection

    def get_connection_configuration(self):
        """Returns a dict with the configuration for the SQL connection
        """
        config = {}
        params = ["host", "port", "database", "user", "password"]
        for param in params:
            reg_id = "senaite.sqlmultiplex.{}".format(param)
            config.update(api.get_registry_record(reg_id))
        return config

    def get_default_attributes(self, obj):
        portal_type = api.get_portal_type(obj)
        return dict(TYPES_TO_MULTIPLEX).get(portal_type, [])

    def supports_multiplex(self, obj):
        """Returns whether the obj supports multiplex
        """
        return len(self.get_default_attributes(obj)) > 0

    @check_installed
    def index(self, obj, attributes=None):
        if not self.supports_multiplex(obj):
            return

        if attributes is None:
            # Get the default columns for this obj
            attributes = self.get_default_attributes(obj)

        if not attributes:
            return

        logger.info("Multiplexer::Indexing {}".format(repr(obj)))

        # Insert the object to the SQL db
        add, data = self.get_insert_sql(obj, attributes)
        self.execute_sql(add, data)

    @check_installed
    def reindex(self, obj, attributes=None, update_metadata=1):
        if not self.supports_multiplex(obj):
            return

        # TODO Update the object from the SQL db
        pass

    @check_installed
    def unindex(self, obj):
        if not self.supports_multiplex(obj):
            return

        # Delete the object from the SQL db

        # Do something here
        logger.info("Multiplexer::Unindexing {}".format(repr(obj)))

    def execute_sql(self, statement, data):
        try:
            cnx = self.mysql_connection
            cursor = cnx.cursor()
            cursor.execute(statement, data)
            cnx.commit()
            cursor.close()
            cnx.close()
            return True
        except mysql.connector.Error as err:
            host = self.get_connection_configuration().get("host")
            msg = "Multiplexer@{} ER#{} ({}): {}".format(host, err.errno,
                                                         err.sqlstate, err.msg)
            # 1146. Table ? does not exist
            logger.error(msg)
        return False

    def get_insert_sql(self, obj, columns):
        record = japi.get_info(obj, complete=True)
        portal_type = api.get_portal_type(obj)

        # Build the base insert thingy
        insert = ("INSERT INTO {} ({}) VALUES ({})".format(
            portal_type, ", ".join(columns), ", ".join(["%s"]*len(columns))))

        # Get the values for the columns
        data = map(lambda column: record.get(column) or "", columns)
        return insert, data

    def begin(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass
