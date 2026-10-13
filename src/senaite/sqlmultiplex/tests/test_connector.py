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

"""Tests for the PostgreSQL connector

The PostgreSQL tests run against a real server and are skipped unless
SENAITE_SQLMULTIPLEX_TEST_DSN is set, e.g.:

    SENAITE_SQLMULTIPLEX_TEST_DSN="dbname=sqlmultiplex_test" bin/test

They create and drop tables prefixed with "sqlmultiplex_test_".
"""

import os
import threading
import unittest

import psycopg2
from psycopg2.extras import Json
from senaite.sqlmultiplex.connector import PostgreSQLConnector
from senaite.sqlmultiplex.connector import to_parameter
from senaite.sqlmultiplex.row import SQLRow

TEST_DSN = os.environ.get("SENAITE_SQLMULTIPLEX_TEST_DSN")
TABLE = "sqlmultiplex_test_row"


class Row(SQLRow):
    """Row adapter for a plain dict instead of a content object
    """
    table = TABLE
    columns = (
        ("uid", "varchar(32)"),
        ("title", "text"),
        ("count", "integer"),
        ("data", "jsonb"),
    )

    def get_uid(self):
        return self.context["uid"]

    def get_title(self):
        return self.context.get("title")

    def get_count(self):
        return self.context.get("count")

    def get_data(self):
        return self.context.get("data")


class WideRow(Row):
    """Same table with an additional column
    """
    columns = Row.columns + (("extra", "text"), )

    def get_extra(self):
        return "extra"


class Worker(threading.Thread):
    """Long-lived thread that runs functions on request, like a ZServer
    worker thread
    """

    def __init__(self):
        threading.Thread.__init__(self)
        self.daemon = True
        self.condition = threading.Condition()
        self.func = None
        self.start()

    def run(self):
        while True:
            with self.condition:
                while self.func is None:
                    self.condition.wait()
                self.result = self.func()
                self.func = None
                self.condition.notify()

    def call(self, func):
        with self.condition:
            self.func = func
            self.condition.notify()
            while self.func is not None:
                self.condition.wait()
        return self.result


class ToParameterTest(unittest.TestCase):

    def test_wraps_json_values(self):
        self.assertIsInstance(to_parameter({"a": 1}, "jsonb"), Json)
        self.assertIsInstance(to_parameter([1], " JSON "), Json)

    def test_keeps_other_values(self):
        self.assertEqual(to_parameter(1, "integer"), 1)
        self.assertIsNone(to_parameter(None, "jsonb"))


class SQLRowTest(unittest.TestCase):

    def test_values_call_one_getter_per_column(self):
        row = Row({"uid": "u1", "title": "T", "count": 2, "data": None})
        self.assertEqual(row.values(), {
            "uid": "u1", "title": "T", "count": 2, "data": None})
        self.assertEqual(row.key(), "u1")

    def test_missing_getter_raises(self):
        class IncompleteRow(Row):
            columns = Row.columns + (("missing", "text"), )

        row = IncompleteRow({"uid": "u1"})
        self.assertRaises(NotImplementedError, row.values)


@unittest.skipUnless(TEST_DSN, "SENAITE_SQLMULTIPLEX_TEST_DSN not set")
class PostgreSQLConnectorTest(unittest.TestCase):

    def setUp(self):
        self.drop_table()
        self.connector = self.make_connector()

    def tearDown(self):
        self.connector.rollback()
        self.connector.discard()
        self.drop_table()

    def make_connector(self):
        connector = PostgreSQLConnector()
        connector.connect = lambda: psycopg2.connect(TEST_DSN)
        return connector

    def query(self, statement):
        """Runs a query on a separate connection, i.e. sees only
        committed data
        """
        conn = psycopg2.connect(TEST_DSN)
        try:
            with conn.cursor() as cursor:
                cursor.execute(statement)
                return cursor.fetchall()
        finally:
            conn.close()

    def drop_table(self):
        conn = psycopg2.connect(TEST_DSN)
        with conn.cursor() as cursor:
            cursor.execute('DROP TABLE IF EXISTS "{}"'.format(TABLE))
        conn.commit()
        conn.close()

    def get_uids(self):
        return [r[0] for r in self.query(
            'SELECT uid FROM "{}" ORDER BY uid'.format(TABLE))]

    def test_rows_are_visible_after_commit_only(self):
        self.assertTrue(self.connector.upsert(Row({"uid": "u1"})))
        self.connector.commit()
        self.assertTrue(self.connector.upsert(Row({"uid": "u2"})))
        self.assertEqual(self.get_uids(), ["u1"])
        self.connector.commit()
        self.assertEqual(self.get_uids(), ["u1", "u2"])

    def test_upsert_updates_existing_row(self):
        self.connector.upsert(Row({"uid": "u1", "title": "old"}))
        self.connector.upsert(Row({"uid": "u1", "title": "new", "count": 3}))
        self.connector.commit()
        self.assertEqual(
            self.query('SELECT uid, title, count FROM "{}"'.format(TABLE)),
            [("u1", "new", 3)])

    def test_json_column(self):
        data = {"interims": [{"keyword": "A", "value": "1.0"}]}
        self.connector.upsert(Row({"uid": "u1", "data": data}))
        self.connector.commit()
        self.assertEqual(
            self.query('SELECT data FROM "{}"'.format(TABLE)), [(data, )])

    def test_rollback_discards_rows(self):
        self.connector.upsert(Row({"uid": "u1"}))
        self.connector.commit()
        self.connector.upsert(Row({"uid": "u2"}))
        self.connector.rollback()
        self.connector.commit()
        self.assertEqual(self.get_uids(), ["u1"])

    def test_rolled_back_table_is_created_again(self):
        """The CREATE TABLE of a rolled back transaction must not be
        remembered as existing
        """
        self.connector.upsert(Row({"uid": "u1"}))
        self.connector.rollback()
        self.assertTrue(self.connector.upsert(Row({"uid": "u2"})))
        self.connector.commit()
        self.assertEqual(self.get_uids(), ["u2"])

    def test_rejected_row_keeps_other_rows(self):
        self.connector.upsert(Row({"uid": "u1"}))
        self.assertFalse(
            self.connector.upsert(Row({"uid": "u2", "count": "many"})))
        self.assertTrue(self.connector.upsert(Row({"uid": "u3"})))
        self.connector.commit()
        self.assertEqual(self.get_uids(), ["u1", "u3"])

    def test_missing_column_is_added(self):
        self.connector.upsert(Row({"uid": "u1"}))
        self.connector.commit()
        connector = self.make_connector()
        self.assertTrue(connector.upsert(WideRow({"uid": "u2"})))
        connector.commit()
        connector.discard()
        self.assertEqual(
            self.query('SELECT uid, extra FROM "{}" ORDER BY uid'
                       .format(TABLE)),
            [("u1", None), ("u2", "extra")])

    def test_descriptions_become_column_comments(self):
        """Reporting tools show column comments as field descriptions
        """
        Row.descriptions = {"title": "Title of the object"}
        WideRow.descriptions = {"extra": "Added later"}
        try:
            self.connector.upsert(Row({"uid": "u1"}))
            self.connector.commit()
            self.connector.upsert(WideRow({"uid": "u2"}))
            self.connector.commit()
        finally:
            del Row.descriptions
            del WideRow.descriptions
        self.assertEqual(self.query(
            "SELECT attname, col_description(attrelid, attnum) "
            "FROM pg_attribute WHERE attrelid = '{}'::regclass "
            "AND attname IN ('uid', 'title', 'extra') ORDER BY attname"
            .format(TABLE)),
            [("extra", "Added later"), ("title", "Title of the object"),
             ("uid", None)])

    def test_delete(self):
        self.connector.upsert(Row({"uid": "u1"}))
        self.connector.upsert(Row({"uid": "u2"}))
        self.connector.commit()
        self.assertTrue(self.connector.delete(Row({"uid": "u1"})))
        self.connector.commit()
        self.assertEqual(self.get_uids(), ["u2"])

    def test_delete_without_table(self):
        self.assertTrue(self.connector.delete(Row({"uid": "u1"})))
        self.connector.commit()
        self.assertEqual(self.get_uids(), [])

    def test_threads_have_separate_transactions(self):
        """Thread B aborts after thread A committed. The rows of B must
        not end up in the database.

        The table exists already, as it does after the first run. Writing
        to an existing table takes no lock that blocks the other thread.
        """
        self.connector.upsert(Row({"uid": "x"}))
        self.connector.commit()
        a, b = Worker(), Worker()
        a.call(lambda: self.connector.upsert(Row({"uid": "a"})))
        b.call(lambda: self.connector.upsert(Row({"uid": "b"})))
        a.call(self.connector.commit)
        b.call(self.connector.rollback)
        self.assertEqual(self.get_uids(), ["a", "x"])
        a.call(self.connector.discard)
        b.call(self.connector.discard)

    def test_lost_connection_is_replaced(self):
        self.connector.upsert(Row({"uid": "u1"}))
        self.connector.get_connection().close()
        self.assertTrue(self.connector.upsert(Row({"uid": "u2"})))
        self.connector.commit()
        self.assertEqual(self.get_uids(), ["u2"])

    def test_no_connection_without_dsn(self):
        connector = PostgreSQLConnector()
        connector.connect = lambda: None
        self.assertFalse(connector.is_active())
        self.assertFalse(connector.upsert(Row({"uid": "u1"})))
        connector.commit()
        connector.rollback()
