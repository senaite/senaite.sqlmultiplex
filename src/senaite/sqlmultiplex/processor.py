
import json

import mysql.connector
from bika.lims import api
from mysql.connector import errorcode
from Products.CMFCore.interfaces import IPortalCatalogQueueProcessor
from senaite.app.supermodel.model import SuperModel
from senaite.sqlmultiplex import check_installed
from senaite.sqlmultiplex import logger
from zope.interface import implementer

# TODO Get this dynamically instead
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

    @property
    def mysql_connection(self):
        """Returns the connection to the destination database
        """
        config = self.get_connection_configuration()
        return mysql.connector.connect(**config)

    def get_connection_configuration(self):
        """Returns a dict with the configuration for the SQL connection
        """
        config = {}
        params = ["host", "port", "database", "user", "password"]
        for param in params:
            reg_id = "senaite.sqlmultiplex.{}".format(param)
            config.update({param: api.get_registry_record(reg_id)})
        return config

    def get_default_attributes(self, obj):
        """Returns the default attributes from the object to keep mapped
        against the SQL database
        """
        portal_type = api.get_portal_type(obj)
        # TODO Get this from somewhere instead of a const
        attrs = dict(TYPES_TO_MULTIPLEX).get(portal_type, [])
        # Always inject the UID
        if attrs and "UID" not in attrs:
            attrs.append("UID")
        return attrs

    def supports_multiplex(self, obj):
        """Returns whether the obj supports multiplex
        """
        return len(self.get_default_attributes(obj)) > 0

    @check_installed
    def index(self, obj, attributes=None):
        if not self.supports_multiplex(obj):
            return

        if not attributes:
            # Get the default columns for this obj
            attributes = self.get_default_attributes(obj)

        if not attributes:
            logger.debug("SKIP. No attributes set for {}".format(repr(obj)))
            return

        logger.info("Multiplexer::Indexing {}".format(repr(obj)))

        # Insert the object to the SQL db
        operation, params = self.get_insert_operation(obj, attributes)
        try:
            self.execute(operation, params)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_NO_SUCH_TABLE:
                # TODO Better to do this out of here
                try:
                    self.create_table_for(obj, attributes)
                    # And retry
                    self.execute(operation, params)
                except:
                    return

    @check_installed
    def reindex(self, obj, attributes=None, update_metadata=1):
        # TODO Update the object from the SQL db?
        self.index(obj, attributes=attributes)
        pass

    @check_installed
    def unindex(self, obj):
        if not self.supports_multiplex(obj):
            return

        # Delete the object from the SQL db

        # Do something here
        logger.info("Multiplexer::Unindexing {}".format(repr(obj)))

    def execute(self, operation, params=None, raise_error=True):
        """Executes the given database operation (query or command). The
        parameters found in the tuple params are bound to the variables in the
        operation. Specify variables using %s or %(name)s parameter style
        :param operation: SQL query or command
        :param data: variables for the operation
        """
        cnx = self.mysql_connection
        cursor = cnx.cursor()
        succeed = False
        try:
            cursor.execute(operation, params=params)
            cnx.commit()
            succeed = True
        except mysql.connector.Error as err:
            host = self.get_connection_configuration().get("host")
            msg = "Multiplexer@{} ER#{} ({}): {}".format(
                host, err.errno,err.sqlstate, err.msg)
            logger.error(msg)
            if raise_error:
                raise err
        finally:
            try:
                logger.info(cursor.statement)
            except:
                pass
            cursor.close()
            cnx.close()

        return succeed

    def create_table_for(self, obj, attributes, raise_error=True):
        operation = self.get_table_create(obj, attributes)
        try:
            self.execute(operation)
        except mysql.connector.Error as err:
            host = self.get_connection_configuration().get("host")
            msg = "Multiplexer@{} ER#{} ({}): {}".format(
                host, err.errno,err.sqlstate, err.msg)
            logger.error(msg)
            if raise_error:
                raise raise_error

    def get_table_create(self, obj, attributes):
        portal_type = api.get_portal_type(obj)

        def to_column(attribute):
            # TODO We just always assume a varchar type here!
            return "`{}` varchar(191) NULL".format(attribute)

        # Build the create table operation
        base = "CREATE TABLE `{}` ({}, PRIMARY KEY (`UID`)) ENGINE=InnoDB " \
               "DEFAULT CHARSET=utf8mb4"
        cols = ", ".join(map(to_column, attributes))
        return base.format(portal_type, cols)

    def get_insert_operation(self, obj, attributes):
        """Returns a tuple of two values: SQL insert operation, and operation
        parameters values. The name of the SQL table is the portal type.
        Attributes represent both obj functions/attributes and SQL columns.
        :param obj: the object to insert
        :param attributes: attributes/columns from the object to be inserted
        """
        # TODO Use supermodel instead (this is wonky because depends on request)
        record = self.get_info(obj, attributes)
        portal_type = api.get_portal_type(obj)

        # Build the base insert thingy
        insert = ("INSERT INTO {} ({}) VALUES ({})".format(
            portal_type,
            ", ".join(attributes),
            ", ".join(["%s"]*len(attributes)))
        )

        # Get the values for the columns
        data = map(lambda column: record.get(column) or "", attributes)
        return insert, data

    def get_info(self, obj, attributes=None):
        """Returns a dict with the information of the object, suitable for SQL
        operations
        """
        if attributes is None:
            attributes = []

        info = {}
        sm = SuperModel(obj)

        # Generate a dict with the requested attributes only
        for name in attributes:
            info[name] = sm.stringify(sm.get(name, ""))

        # Sanitize the dict values to hold values suitable for SQL
        for k in info.keys():
            v = info.get(k)
            if isinstance(v, (list, tuple, dict)):
                info.update({v: json.dumps(v)})

        return info

    def begin(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass
