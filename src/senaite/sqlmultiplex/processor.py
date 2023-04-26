from senaite.sqlmultiplex import check_enabled
from senaite.sqlmultiplex import logger
from senaite.sqlmultiplex import utils
from senaite.sqlmultiplex.connectors.mysql import MySqlConnector
from senaite.sqlmultiplex.connectors.psql import PostgreSqlConnector


class CatalogMultiplexProcessor(object):
    """A catalog multiplex processor
    """

    def get_connector(self):
        """Returns the suitable connector for the database
        """
        conn_type = utils.get_connector_type()
        if conn_type == "MySQL":
            connector = MySqlConnector()
        elif conn_type == "PostgreSQL":
            connector = PostgreSqlConnector()
        else:
            return None
        if not connector.is_supported():
            return None
        return connector

    @check_enabled
    def index(self, obj, attributes=None):
        if not utils.supports_multiplex(obj):
            return

        # get the connector
        connector = self.get_connector()
        if not connector:
            logger.error("Multiplexer::No SQL connector or not supported")
            return

        # insert or update the object in the sql database
        logger.info("Multiplexer::Indexing {}".format(repr(obj)))
        connector.insert_or_update(obj)

    @check_enabled
    def reindex(self, obj, attributes=None, update_metadata=1):
        self.index(obj, attributes=attributes)

    @check_enabled
    def unindex(self, obj):
        if not utils.supports_multiplex(obj):
            return

        # get the connector
        connector = self.get_connector()
        if not connector:
            logger.error("Multiplexer::No SQL connector or not supported")
            return

        # Delete the object from the SQL db
        logger.info("Multiplexer::Unindexing {}".format(repr(obj)))
        connector.delete(obj)

    def begin(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass
