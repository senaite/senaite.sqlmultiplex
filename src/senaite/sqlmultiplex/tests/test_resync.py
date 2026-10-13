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

"""Unit tests for the resync, with a recording connector and a catalog
stand-in
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


class Brain(object):
    """A catalog brain whose object is a list of rows, or None for an
    object deleted after the query
    """

    def __init__(self, uid, rows):
        self.uid = uid
        self.rows = rows

    def getPath(self):
        return "/senaite/" + self.uid


class API(object):
    """Stands in for bika.lims.api
    """

    def get_portal(self):
        return Portal()

    def get_uid(self, brain):
        return brain.uid


class Catalog(object):
    """Answers the batch queries of the resync: sorted by UID, from the
    given UID on (inclusive, like a range query with min)
    """

    def __init__(self, brains):
        self.brains = brains
        self.queries = []

    def search(self, catalog_id, query):
        self.queries.append(query)
        brains = sorted(self.brains, key=lambda brain: brain.uid)
        start = query.get("UID", {}).get("query")
        if start:
            brains = [brain for brain in brains if brain.uid >= start]
        return brains


class Transaction(object):
    """Records the ends of the ZODB transaction into the connector calls
    """

    def __init__(self, connector):
        self.connector = connector

    def abort(self):
        self.connector.calls.append(("abort", None))


def make_brains(count):
    return [Brain("uid{:02d}".format(num), [Row("r{:02d}".format(num))])
            for num in range(count)]


class ResyncTest(unittest.TestCase):

    def setUp(self):
        self.connector = Connector()
        self.sleeps = []
        self.originals = {}
        self.catalog = Catalog(make_brains(5))
        self.patch("search", self.catalog.search)
        self.patch("get_object", lambda brain: brain.rows)
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

    def test_batch_starts_after_the_uid(self):
        result = resync.resync_batch(
            self.connector, "catalog", {}, after="uid01", size=2)
        self.assertEqual(self.calls("upsert"), ["r02", "r03"])
        self.assertEqual(result, {
            "objects": 2, "rows": 2, "last": "uid03", "done": False})
        self.assertEqual(self.calls("commit"), [None])

    def test_last_batch_is_done(self):
        result = resync.resync_batch(
            self.connector, "catalog", {}, after="uid03", size=2)
        self.assertEqual(self.calls("upsert"), ["r04"])
        self.assertTrue(result["done"])
        self.assertEqual(result["last"], "uid04")

    def test_empty_batch_keeps_the_position(self):
        result = resync.resync_batch(
            self.connector, "catalog", {}, after="uid04", size=2)
        self.assertEqual(result, {
            "objects": 0, "rows": 0, "last": "uid04", "done": True})

    def test_batch_query_is_sorted_and_paged_by_uid(self):
        query = resync.make_batch_query(
            {"portal_type": "Analysis"}, "uid07", 200)
        self.assertEqual(query, {
            "portal_type": "Analysis", "sort_on": "UID", "sort_limit": 201,
            "UID": {"query": "uid07", "range": "min"}})
        self.assertNotIn("UID", resync.make_batch_query({}, None, 200))

    def test_objects_added_during_the_run_do_not_shift_batches(self):
        """Paging by position would skip an object here
        """
        resync.resync_batch(self.connector, "catalog", {}, size=2)
        self.catalog.brains.insert(0, Brain("uid00a", [Row("new")]))
        result = resync.resync_batch(
            self.connector, "catalog", {}, after="uid01", size=2)
        self.assertEqual(self.calls("upsert"), ["r00", "r01", "r02", "r03"])
        self.assertEqual(result["last"], "uid03")

    def test_resync_ends_the_transaction_every_batch(self):
        objects, rows = resync.resync(
            self.connector, "catalog", {}, size=2, pause=0.5)
        self.assertEqual((objects, rows), (5, 5))
        kinds = [call for call, name in self.connector.calls]
        self.assertEqual(kinds, [
            "upsert", "upsert", "commit", "abort",
            "upsert", "upsert", "commit", "abort",
            "upsert", "commit", "abort",
        ])
        self.assertEqual(self.sleeps, [0.5, 0.5])

    def test_resync_resumes_after_the_uid(self):
        objects, rows = resync.resync(
            self.connector, "catalog", {}, after="uid02")
        self.assertEqual(self.calls("upsert"), ["r03", "r04"])

    def test_deleted_objects_are_skipped(self):
        self.catalog.brains[1].rows = None
        self.patch("get_object", lambda brain: brain.rows)
        objects, rows = resync.resync(self.connector, "catalog", {})
        self.assertEqual((objects, rows), (4, 4))

    def test_failed_rows_are_not_counted(self):
        self.connector.upsert = lambda row: row.name != "r01"
        objects, rows = resync.resync(self.connector, "catalog", {})
        self.assertEqual((objects, rows), (5, 4))


class ParseArgsTest(unittest.TestCase):

    def test_defaults(self):
        options = resync.parse_args(["-c", "senaite_catalog_analysis"])
        self.assertEqual(options.site, "senaite")
        self.assertEqual(options.catalog, "senaite_catalog_analysis")
        self.assertIsNone(options.portal_types)
        self.assertEqual(options.batch_size, resync.BATCH_SIZE)
        self.assertEqual(options.pause, 0.0)
        self.assertIsNone(options.after)

    def test_options(self):
        options = resync.parse_args(
            ["-c", "senaite_catalog", "-t", "Analysis",
             "-t", "AnalysisRequest", "-b", "50",
             "-p", "0.2", "--after", "abc"])
        self.assertEqual(options.portal_types,
                         ["Analysis", "AnalysisRequest"])
        self.assertEqual(options.batch_size, 50)
        self.assertEqual(options.pause, 0.2)
        self.assertEqual(options.after, "abc")

    def test_query(self):
        self.assertEqual(resync.make_query(None), {})
        self.assertEqual(resync.make_query(["Analysis"]),
                         {"portal_type": ["Analysis"]})


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ResyncTest))
    suite.addTest(unittest.makeSuite(ParseArgsTest))
    return suite
