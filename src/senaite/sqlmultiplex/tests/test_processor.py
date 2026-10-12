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

"""Unit tests for the queue processor, with a recording connector
"""

import unittest

from senaite.sqlmultiplex import processor
from senaite.sqlmultiplex.processor import SQLMultiplexProcessor


class Row(object):

    def __init__(self, name, applies=True):
        self.name = name
        self._applies = applies

    def applies(self):
        return self._applies


class Connector(object):
    """Records the calls of the processor
    """

    def __init__(self):
        self.calls = []

    def upsert(self, row):
        self.calls.append(("upsert", row.name))
        return True

    def delete(self, row):
        self.calls.append(("delete", row.name))
        return True

    def commit(self):
        self.calls.append(("commit", None))

    def rollback(self):
        self.calls.append(("rollback", None))


class SQLMultiplexProcessorTest(unittest.TestCase):

    def setUp(self):
        self.connector = Connector()
        self.rows = []
        self.enabled = True
        self.originals = {}
        self.patch("is_enabled", lambda: self.enabled)
        self.patch("get_rows", lambda obj: self.rows)
        self.patch("get_connector", lambda: self.connector)
        self.patch("query_connector", lambda: self.connector)
        self.processor = SQLMultiplexProcessor()

    def tearDown(self):
        for name, func in self.originals.items():
            setattr(processor, name, func)

    def patch(self, name, func):
        self.originals[name] = getattr(processor, name)
        setattr(processor, name, func)

    def test_index_upserts_rows_that_apply(self):
        self.rows = [Row("a"), Row("b", applies=False)]
        self.processor.index(object())
        self.assertEqual(
            self.connector.calls, [("upsert", "a"), ("delete", "b")])

    def test_reindex_behaves_like_index(self):
        self.rows = [Row("a")]
        self.processor.reindex(object())
        self.assertEqual(self.connector.calls, [("upsert", "a")])

    def test_unindex_deletes_rows(self):
        self.rows = [Row("a")]
        self.processor.unindex(object())
        self.assertEqual(self.connector.calls, [("delete", "a")])

    def test_commit_and_abort(self):
        self.processor.commit()
        self.processor.abort()
        self.assertEqual(
            self.connector.calls, [("commit", None), ("rollback", None)])

    def test_disabled_does_nothing(self):
        self.enabled = False
        self.rows = [Row("a")]
        self.processor.index(object())
        self.processor.unindex(object())
        self.processor.commit()
        self.processor.abort()
        self.assertEqual(self.connector.calls, [])

    def test_no_connection_does_nothing(self):
        self.patch("get_connector", lambda: None)
        self.rows = [Row("a")]
        self.processor.index(object())
        self.processor.unindex(object())
        self.assertEqual(self.connector.calls, [])
