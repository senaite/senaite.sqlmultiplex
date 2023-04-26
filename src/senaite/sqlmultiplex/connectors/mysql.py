from senaite.sqlmultiplex import logger
from senaite.sqlmultiplex.config import CUSTOM_TYPES
from senaite.sqlmultiplex.connectors import SqlConnector
from six import string_types

from bika.lims import api

try:
    import mysql.connector
    from mysql.connector import errorcode
    MYSQL_SUPPORTED = True
except ImportError:
    MYSQL_SUPPORTED = False

CONNECTOR_ID = "senaite.sqlmultiplex.connectors.mysql"

COLUMN_UID = "UID"

DEFAULT_COLUMN_TYPE = "TEXT"

CREATE_TABLE_TEMPLATE = \
    "CREATE TABLE `{table_name}` (" \
    " {column_uid} CHAR(32)," \
    " {columns_create}," \
    " PRIMARY KEY (`{column_uid}')" \
    ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"

COLUMN_CREATE_DEFINITION = "`{name}` {type} {constraint}"

INSERT_UPDATE_TEMPLATE = \
    "INSERT INTO {table_name} ({columns}) " \
    "VALUES ({sql_params}) " \
    "ON DUPLICATE KEY UPDATE {values_update}"

DELETE_TEMPLATE = "DELETE FROM {table_name} WHERE {column_uid}='{uid}'"

UNQUOTED_TYPES = (
    "TINYINT",
    "SMALLINT"
    "MEDIUMINT",
    "BIGINT",
    "DECIMAL",
    "NUMERIC",
    "FLOAT",
    "DOUBLE",
    "BOOLEAN",
)

DATA_TYPES = (
    ("string", "text"),
    ("boolean", "BOOLEAN"),
    ("fixedpoint", "DOUBLE"),
    ("duration", "JSON"),
    ("integer", "BIGINT"),
    ("float", "DOUBLE"),
    ("records", "JSON"),
    ("datetime", "TEXT"),  # do converter
    ("lines", "JSON"),
    ("computed", "TEXT")
)


class MySqlConnector(SqlConnector):
    _connection = None
    connector_id = CONNECTOR_ID
    column_uid = COLUMN_UID
    default_column_type = DEFAULT_COLUMN_TYPE
    create_table_template = CREATE_TABLE_TEMPLATE
    column_definition_template = COLUMN_CREATE_DEFINITION
    insert_update_template = INSERT_UPDATE_TEMPLATE
    delete_template = DELETE_TEMPLATE
    unquoted_types = UNQUOTED_TYPES

    def is_supported(self):
        """Returns whether this connector is supported
        """
        return MYSQL_SUPPORTED

    def get_connection(self):
        """Returns the connection to the destination database
        """
        if not self._connection or self._connection.closed:
            self._connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                database=self.dbname,
                user=self.username,
                password=self.password
            )
        return self._connection

    def get_insert_update(self, obj):
        """Returns a tuple of two values: SQL insert-update operation, and
        operation parameters values.
        :param obj: the object to insert
        """
        obj_info = self.get_info(obj)
        columns = obj_info.keys()
        q_columns = map(lambda a: "`{}`".format(a), columns)
        values = [obj_info.get(column) for column in columns]
        values_update = map(lambda v: "{}=VALUES({})".format(v, v), q_columns)
        params = {
            "table_name": self.get_table_name(obj),
            "columns": ", ".join(q_columns),
            "column_uid": self.column_uid,
            "sql_params": ", ".join(["%s"] * len(values)),
            "values_update": ", ".join(values_update),
        }
        statement = self.insert_update_template.format(**params)
        return statement, values

    def get_column_type(self, obj, field):
        sql_type = self.default_column_type
        if isinstance(field, string_types):
            return "TEXT"

        portal_type = api.get_portal_type(obj)
        custom_types = dict(CUSTOM_TYPES).get(portal_type, {})
        custom_type = custom_types.get(field.getName())
        if custom_type:
            return custom_type

        if self.is_string_field(field):
            widget = getattr(field, "widget", None)
            max_length = getattr(widget, "max_length", 255)
            return "VARCHAR({})".format(max_length)

        elif self.is_reference_field(field):
            if field.multiValued:
                return "JSON"
            return "CHAR({})".format(32)

        data_types = dict(DATA_TYPES)
        return data_types.get(field.type, sql_type)

    def insert_or_update(self, obj):
        """Inserts or updates the given object
        """
        # Insert the object to the SQL db
        operation, params = self.get_insert_update(obj)
        try:
            self.execute(operation, params)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_NO_SUCH_TABLE:
                # try to create the table
                create_table = self.get_create_table_statement(obj)
                self.execute(create_table, raise_error=self.raise_errors)
                # retry the insert update
                self.execute(operation, params, raise_error=self.raise_errors)
            elif self.raise_errors:
                raise err

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
                self.host, self.port, err.errno, err.sqlstate, err.msg)
            logger.error(msg)
            if raise_error:
                raise err
        finally:
            try:
                logger.info("*" * 79)
                logger.info(cursor.statement)
                logger.info("*" * 79)
            except:
                pass
            cursor.close()
            cnx.close()
        return succeed
