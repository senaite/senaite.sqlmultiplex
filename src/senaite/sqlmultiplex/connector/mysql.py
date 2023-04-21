from bika.lims import api
from senaite.sqlmultiplex import logger
try:
    import mysql.connector
    from mysql.connector import errorcode
    MYSQL_SUPPORTED = True
except ImportError:
    MYSQL_SUPPORTED = False

from senaite.sqlmultiplex.connector import SqlConnector


class MySqlConnector(SqlConnector):

    def is_supported(self):
        """Returns whether this connector is supported
        """
        return MYSQL_SUPPORTED

    def get_connection(self):
        """Returns the connection to the destination database
        """
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            database=self.dbname,
            user=self.username,
            password=self.password
        )

    def create_table_for(self, obj, attributes, raise_error=True):
        operation = self.get_table_create(obj, attributes)
        try:
            self.execute(operation)
        except mysql.connector.Error as err:
            msg = "Multiplexer@{}:{} ER#{} ({}): {}".format(
                self.host, self.port, err.errno,err.sqlstate, err.msg)
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
        operation = base.format(portal_type, cols)
        logger.info(operation)
        return operation

    def get_insert_update(self, obj, attributes):
        """Returns a tuple of two values: SQL insert-update operation, and
        operation parameters values. The name of the SQL table is the portal
        type. Attributes represent both obj functions/attributes and SQL columns
        :param obj: the object to insert
        :param attributes: attributes/columns from the object to be inserted
        """
        record = self.get_info(obj, attributes)
        portal_type = api.get_portal_type(obj)

        # Build the base insert/update thingy
        attrs = map(lambda a: "`{}`".format(a), attributes)
        update_values = map(lambda v: "{}=VALUES({})".format(v, v), attrs)
        insert = "INSERT INTO {} ({}) VALUES ({}) ON DUPLICATE KEY UPDATE {}" \
            .format(portal_type, ", ".join(attrs),
                    ", ".join(["%s"]*len(attrs)),
                    ", ".join(update_values))

        # Get the values for the columns
        data = map(lambda column: record.get(column) or "", attributes)
        return insert, data

    def insert_or_update(self, obj, attributes):
        # Insert the object to the SQL db
        operation, params = self.get_insert_update(obj, attributes)
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
                    pass

    def execute(self, operation, params=None, raise_error=True):
        """Executes the given database operation (query or command). The
        parameters found in the tuple params are bound to the variables in the
        operation. Specify variables using %s or %(name)s parameter style
        :param operation: SQL query or command
        :param data: variables for the operation
        """
        cnx = self.get_connection()
        cursor = cnx.cursor()
        succeed = False
        try:
            cursor.execute(operation, params=params)
            cnx.commit()
            succeed = True
        except mysql.connector.Error as err:
            msg = "Multiplexer@{}:{} ER#{} ({}): {}".format(
                self.host, self.port, err.errno,err.sqlstate, err.msg)
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
