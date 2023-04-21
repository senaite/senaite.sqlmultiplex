from senaite.sqlmultiplex import check_enabled
from senaite.sqlmultiplex import logger
from senaite.sqlmultiplex.config import NON_SUPPORTED_FIELD_NAMES
from senaite.sqlmultiplex.config import NON_SUPPORTED_FIELD_TYPES
from senaite.sqlmultiplex.connector.mysql import MySqlConnector

from bika.lims import api


class CatalogMultiplexProcessor(object):
    """A catalog multiplex processor
    """

    def get_multiplexed_types(self):
        """Returns the list of portal types to be multiplexed
        """
        reg_id = "senaite.sqlmultiplex.content_types"
        return api.get_registry_record(reg_id, [])

    def get_supported_attributes(self, obj):
        """Returns the names of the fields from the object to keep mapped
        against the SQL database
        """
        portal_type = api.get_portal_type(obj)
        if portal_type not in self.get_multiplexed_types():
            return []

        def is_field_supported(field):
            if field.getName() in NON_SUPPORTED_FIELD_NAMES:
                return False
            if field.type in NON_SUPPORTED_FIELD_TYPES:
                return False
            return True

        # Grab only attributes that make sense!
        fields = api.get_fields(obj).values()
        fields = filter(is_field_supported, fields)

        # Get the ids of the fields to store
        attrs = map(lambda f: f.getName(), fields)
        if not attrs:
            return []

        # Always keep the UID
        if "UID" not in attrs:
            attrs.append("UID")
        return attrs

    def supports_multiplex(self, obj):
        """Returns whether the obj supports multiplex
        """
        return api.get_portal_type(obj) in self.get_multiplexed_types()

    def get_connector(self):
        """Returns the suitable connector for the database
        """
        return MySqlConnector()

    @check_enabled
    def index(self, obj, attributes=None):
        if not self.supports_multiplex(obj):
            return

        # always insert/update all fields from the object that make sense
        attributes = self.get_supported_attributes(obj)
        if not attributes:
            logger.debug("SKIP. No attributes set for {}".format(repr(obj)))
            return

        # get the connector
        connector = self.get_connector()
        if not connector:
            logger.error("Cannot SQL multiplex - No connector")
            return

        if not connector.is_supported():
            logger.error("Cannot SQL multiplex - Connector is not supported")
            return

        # insert or update the object in the sql database
        logger.info("Multiplexer::Indexing {}".format(repr(obj)))
        try:
            connector.insert_or_update(obj, attributes)
        except Exception as e:
            logger.error("Cannot insert/update {}: {}".format(obj, e.message))
            return

    def reindex(self, obj, attributes=None, update_metadata=1):
        self.index(obj, attributes=attributes)

    @check_enabled
    def unindex(self, obj):
        if not self.supports_multiplex(obj):
            return

        # Delete the object from the SQL db
        uid = api.get_uid(obj)
        portal_type = api.get_portal_type(obj)
        operation = "DELETE FROM {} WHERE UID='{}'".format(portal_type, uid)
        self.execute(operation, raise_error=False)

        # Do something here
        logger.info("Multiplexer::Unindexing {}".format(repr(obj)))

    def begin(self):
        pass

    def commit(self):
        pass

    def abort(self):
        pass
