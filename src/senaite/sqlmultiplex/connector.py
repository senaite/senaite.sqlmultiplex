# -*- coding: utf-8 -*-
#
# This file is part of SENAITE.SQLMULTIPLEX.
#
# SENAITE.SQLMULTIPLEX is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation, version 2.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# Copyright 2020-2026 by it's authors.
# Some rights reserved, see README and LICENSE.

import os
import threading

import psycopg2
from bika.lims import api
from psycopg2.extras import Json
from senaite.sqlmultiplex import logger
from senaite.sqlmultiplex import statements
from senaite.sqlmultiplex.config import DSN_ENVIRONMENT_VARIABLE
from senaite.sqlmultiplex.config import REGISTRY_DSN
from senaite.sqlmultiplex.interfaces import ISQLConnector
from zope.interface import implementer

SAVEPOINT = "SAVEPOINT sqlmultiplex"
RELEASE_SAVEPOINT = "RELEASE SAVEPOINT sqlmultiplex"
ROLLBACK_TO_SAVEPOINT = "ROLLBACK TO SAVEPOINT sqlmultiplex"


def is_json_type(sql_type):
    """Returns whether the SQL type is json or jsonb
    """
    return sql_type.strip().lower().startswith("json")


def to_parameter(value, sql_type):
    """Returns the value as a statement parameter for the column type
    """
    if value is not None and is_json_type(sql_type):
        return Json(value)
    return value


def get_schema(row):
    """Returns the set of (table, column) pairs the row writes to
    """
    return set((row.table, name) for name, sql_type in row.columns)


@implementer(ISQLConnector)
class PostgreSQLConnector(object):
    """PostgreSQL connector

    A global utility shared by all ZServer threads. Each thread holds
    its own connection, so one ZODB transaction maps to exactly one
    PostgreSQL transaction. Every row is written inside a savepoint: a
    rejected row is logged and skipped without losing the other rows of
    the transaction.
    """

    def __init__(self):
        self._local = threading.local()
        # (table, column) pairs known to exist, shared by all threads.
        # Only filled after a commit, so that a rolled back CREATE TABLE
        # is not mistaken for an existing table.
        self._schema = set()
        self._lock = threading.Lock()

    @property
    def dsn(self):
        """Returns the libpq connection string

        The environment variable takes precedence over the registry.
        """
        dsn = os.environ.get(DSN_ENVIRONMENT_VARIABLE)
        if dsn:
            return dsn
        return api.get_registry_record(REGISTRY_DSN)

    def connect(self):
        """Opens a new connection or returns None on failure
        """
        dsn = self.dsn
        if not dsn:
            return None
        try:
            return psycopg2.connect(dsn)
        except psycopg2.OperationalError as exc:
            logger.error("Cannot connect to PostgreSQL: %s", exc)
        return None

    def get_connection(self, create=True):
        """Returns the connection of the current thread

        :param create: open a connection if the thread has none
        """
        conn = getattr(self._local, "conn", None)
        if conn is not None and not conn.closed:
            return conn
        if not create:
            return None
        if conn is not None:
            logger.warn("PostgreSQL connection was closed, reconnecting. "
                        "Uncommitted rows of this transaction are lost")
        self._local.conn = self.connect()
        self._local.pending = set()
        return self._local.conn

    def get_pending(self):
        """Returns the (table, column) pairs created in the current
        transaction of this thread
        """
        return getattr(self._local, "pending", set())

    def discard(self):
        """Closes and forgets the connection of the current thread
        """
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            conn.close()
        self._local.conn = None
        self._local.pending = set()

    def is_active(self):
        return self.get_connection() is not None

    def get_missing_columns(self, row):
        """Returns the (table, column) pairs of the row that are not known
        to exist
        """
        with self._lock:
            known = self._schema | self.get_pending()
        return get_schema(row) - known

    def remember_columns(self, columns):
        """Remembers committed (table, column) pairs as existing
        """
        with self._lock:
            self._schema.update(columns)

    def ensure_schema(self, cursor, row):
        """Creates the table and the columns of the row that are missing

        Reads the catalog first and only runs DDL for what is really
        missing: ALTER TABLE locks the table exclusively until commit,
        even if the column exists already.

        Returns the (table, column) pairs created in this transaction.
        """
        missing = self.get_missing_columns(row)
        if not missing:
            return set()
        cursor.execute(statements.table_columns(), [row.table])
        existing = set((row.table, name) for (name, ) in cursor.fetchall())
        self.remember_columns(existing & missing)
        missing = missing - existing
        if not missing:
            return set()
        if not existing:
            cursor.execute(statements.create_table(
                row.table, row.primary_key, row.columns))
        else:
            self.add_columns(cursor, row, missing)
        self.comment_columns(cursor, row, missing)
        return missing

    def add_columns(self, cursor, row, columns):
        """Adds the (table, column) pairs to the existing table
        """
        types = dict(row.columns)
        for table, name in sorted(columns):
            cursor.execute(statements.add_column(table, name, types[name]))

    def comment_columns(self, cursor, row, columns):
        """Sets the descriptions of the row as comments of the new columns
        """
        descriptions = getattr(row, "descriptions", None) or {}
        for table, name in sorted(columns):
            if descriptions.get(name):
                cursor.execute(statements.comment_column(table, name),
                               [descriptions[name]])

    def upsert(self, row):
        values = row.values()
        names = [name for name, sql_type in row.columns]
        params = [
            to_parameter(values.get(name), sql_type)
            for name, sql_type in row.columns
        ]
        upsert = statements.upsert(row.table, row.primary_key, names)
        return self.write(row, upsert, params)

    def delete(self, row):
        delete = statements.delete(row.table, row.primary_key)
        return self.write(row, delete, [row.key()])

    def write(self, row, statement, params):
        """Executes the statement for the row inside a savepoint

        Creates the table and missing columns first. Rolls back to the
        savepoint and returns False if the database rejects anything.
        """
        conn = self.get_connection()
        if conn is None:
            return False
        try:
            with conn.cursor() as cursor:
                cursor.execute(SAVEPOINT)
                created = self.ensure_schema(cursor, row)
                cursor.execute(statement, params)
                cursor.execute(RELEASE_SAVEPOINT)
        except psycopg2.Error as exc:
            logger.error("Cannot write %r to table %r: %s",
                         row.key(), row.table, exc)
            self.rollback_to_savepoint(conn)
            return False
        self.get_pending().update(created)
        return True

    def rollback_to_savepoint(self, conn):
        """Undoes the statements since the savepoint

        Discards the connection if that fails, e.g. because the server
        went away. The transaction is lost then and the next statement
        opens a new connection.
        """
        try:
            with conn.cursor() as cursor:
                cursor.execute(ROLLBACK_TO_SAVEPOINT)
        except psycopg2.Error as exc:
            logger.error("Discarding PostgreSQL connection: %s", exc)
            self.discard()

    def commit(self):
        conn = self.get_connection(create=False)
        if conn is None:
            return
        try:
            conn.commit()
        except psycopg2.Error as exc:
            logger.error("PostgreSQL commit failed: %s", exc)
            self.discard()
            return
        with self._lock:
            self._schema.update(self.get_pending())
        self._local.pending = set()

    def rollback(self):
        conn = self.get_connection(create=False)
        if conn is None:
            return
        self._local.pending = set()
        try:
            conn.rollback()
        except psycopg2.Error as exc:
            logger.error("PostgreSQL rollback failed: %s", exc)
            self.discard()
