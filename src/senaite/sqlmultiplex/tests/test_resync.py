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

"""Unit tests for the resync, with a recording connector
"""

import unittest

from senaite.sqlmultiplex import resync
from senaite.sqlmultiplex.tests.test_processor import Connector
from senaite.sqlmultiplex.tests.test_processor import Row


class Jar(object):

    def cacheGC(self):
        pass


class Portal(object):
    _p_jar = Jar()


class API(object):
    """Stands in for bika.lims.api
    """

    def get_portal(self):
        return Portal()


class Transaction(object):
    """Records the ends of the ZODB transaction into the connector calls
    """

    def __init__(self, connector):
        self.connector = connector

    def abort(self):
        self.connector.calls.append(("abort", None))


class ResyncTest(unittest.TestCase):

    def setUp(self):
        self.connector = Connector()
        self.originals = {}
        self.sleeps = []
        # brains are the objects, every object is a list of rows, and
        # None stands for an object deleted after the catalog query
        self.patch("get_object", lambda brain: brain)
        self.patch("get_rows", lambda obj: obj)
        self.patch("api", API())
        self.patch("transaction", Transaction(self.connector))
        self.patch("time", type("Time", (), {
            "sleep": staticmethod(self.sleeps.append)}))

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(resync, name, value)

    def patch(self, name, value):
        self.originals[name] = getattr(resync, name)
        setattr(resync, name, value)

    def calls(self, kind):
        return [name for call, name in self.connector.calls if call == kind]

    def test_writes_all_rows(self):
        objects = [[Row("a"), Row("b", applies=False)], [Row("c")]]
        total, rows = resync.resync(objects, self.connector)
        self.assertEqual((total, rows), (2, 3))
        self.assertEqual(self.calls("upsert"), ["a", "c"])
        self.assertEqual(self.calls("delete"), ["b"])

    def test_commits_and_ends_the_transaction_every_batch(self):
        """An interrupted run keeps the rows of the finished batches,
        and every batch reads the current state of the ZODB
        """
        objects = [[Row(str(num))] for num in range(5)]
        resync.resync(objects, self.connector, batch_size=2)
        kinds = [call for call, name in self.connector.calls]
        self.assertEqual(kinds, [
            "upsert", "upsert", "commit", "abort",
            "upsert", "upsert", "commit", "abort",
            "upsert", "commit", "abort",
        ])

    def test_pause_between_batches(self):
        objects = [[Row(str(num))] for num in range(5)]
        resync.resync(objects, self.connector, batch_size=2, pause=0.5)
        self.assertEqual(self.sleeps, [0.5, 0.5])

    def test_start_resumes_at_the_position(self):
        objects = [[Row(str(num))] for num in range(5)]
        total, rows = resync.resync(objects, self.connector, start=3)
        self.assertEqual((total, rows), (2, 2))
        self.assertEqual(self.calls("upsert"), ["3", "4"])

    def test_deleted_objects_are_skipped(self):
        total, rows = resync.resync(
            [[Row("a")], None, [Row("c")]], self.connector)
        self.assertEqual((total, rows), (2, 2))

    def test_failed_rows_are_not_counted(self):
        self.connector.upsert = lambda row: row.name != "bad"
        total, rows = resync.resync(
            [[Row("good")], [Row("bad")]], self.connector)
        self.assertEqual((total, rows), (2, 1))


class ParseArgsTest(unittest.TestCase):

    def test_defaults(self):
        options = resync.parse_args(["-c", "senaite_catalog_analysis"])
        self.assertEqual(options.site, "senaite")
        self.assertEqual(options.catalog, "senaite_catalog_analysis")
        self.assertIsNone(options.portal_types)
        self.assertEqual(options.batch_size, resync.BATCH_SIZE)
        self.assertEqual(options.pause, 0.0)
        self.assertEqual(options.start, 0)

    def test_repeated_portal_types(self):
        options = resync.parse_args(
            ["-c", "senaite_catalog", "-t", "Analysis",
             "-t", "AnalysisRequest", "-b", "50",
             "-p", "0.2", "--start", "1000"])
        self.assertEqual(options.portal_types,
                         ["Analysis", "AnalysisRequest"])
        self.assertEqual(options.batch_size, 50)
        self.assertEqual(options.pause, 0.2)
        self.assertEqual(options.start, 1000)

    def test_query(self):
        self.assertEqual(resync.make_query(None), {})
        self.assertEqual(resync.make_query(["Analysis"]),
                         {"portal_type": ["Analysis"]})


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ResyncTest))
    suite.addTest(unittest.makeSuite(ParseArgsTest))
    return suite
