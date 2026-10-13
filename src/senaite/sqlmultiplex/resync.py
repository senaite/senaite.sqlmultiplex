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

"""Writes the rows of existing objects into the SQL database

Used to fill a new database, and to repair rows that are missing after
a failed commit. Run it as an instance command:

    bin/instance sqlmultiplex_resync -s senaite \\
        -c senaite_catalog_analysis -t Analysis

The rows are written with the same adapters as the queue processor, so
the result equals what saving every object would produce.

It runs next to live instances without blocking them:

- It is a separate process and uses no request threads of the
  instances. Start it with `nice` on a busy server.
- It reads only. After every batch it commits the rows and ends the
  ZODB transaction, so the next batch reads the current state: an
  object changed in the meantime is never written from an old
  snapshot.
- Small batches keep the PostgreSQL row locks short. A live save of
  the same object waits for the end of the batch at most.
- --pause sleeps between the batches to leave room for the instances,
  --start resumes an interrupted run at the given position.
"""

import argparse
import logging
import time

import transaction
from AccessControl.SecurityManagement import newSecurityManager
from AccessControl.SpecialUsers import system
from bika.lims import api
from senaite.sqlmultiplex import logger
from senaite.sqlmultiplex.processor import get_connector
from senaite.sqlmultiplex.processor import get_rows
from senaite.sqlmultiplex.processor import write
from Testing.makerequest import makerequest
from zExceptions import NotFound
from zope.component.hooks import setSite

# Number of objects written before the rows are committed
BATCH_SIZE = 200

# Seconds to sleep between two batches
PAUSE = 0.0


def resync_object(connector, obj):
    """Writes all rows of the object and returns how many succeeded
    """
    return len(filter(None, [write(connector, row)
                             for row in get_rows(obj)]))


def is_batch_end(num, batch_size):
    """Returns whether the num-th object closes a batch
    """
    return num % batch_size == 0


def get_object(brain):
    """Returns the object of the brain, or None if it was deleted after
    the catalog query
    """
    try:
        return brain._unrestrictedGetObject()
    except (KeyError, AttributeError, NotFound):
        logger.warning("Resync: skipping {}, object not found".format(
            brain.getPath()))
        return None


def finish_batch(connector, num, total, pause):
    """Commits the rows of the batch and starts a fresh ZODB transaction

    Ending the transaction makes the next batch read the current state
    of the database instead of the snapshot taken at the start.
    """
    connector.commit()
    transaction.abort()
    api.get_portal()._p_jar.cacheGC()
    logger.info("Resync: {}/{} objects".format(num, total))
    if pause:
        time.sleep(pause)


def resync(brains, connector, batch_size=BATCH_SIZE, start=0,
           pause=PAUSE):
    """Writes the rows of the objects behind the brains

    Starts at position start (0 based). Commits every batch_size
    objects, so an interrupted run keeps the rows written so far.
    Returns the number of objects and the number of rows written.
    """
    total = len(brains)
    objects = 0
    rows = 0
    for num, brain in enumerate(brains[start:], start + 1):
        obj = get_object(brain)
        if obj is not None:
            objects += 1
            rows += resync_object(connector, obj)
        if is_batch_end(num, batch_size):
            finish_batch(connector, num, total, pause)
    connector.commit()
    transaction.abort()
    return objects, rows


def parse_args(args):
    """Parses the command line arguments of the instance command
    """
    parser = argparse.ArgumentParser(
        prog="bin/instance sqlmultiplex_resync",
        description="Write the SQL rows of existing objects")
    parser.add_argument(
        "-s", "--site", default="senaite",
        help="id of the SENAITE site (default: senaite)")
    parser.add_argument(
        "-c", "--catalog", required=True,
        help="catalog to search, e.g. senaite_catalog_analysis")
    parser.add_argument(
        "-t", "--portal-type", action="append", dest="portal_types",
        help="portal type to resync, may be repeated (default: all)")
    parser.add_argument(
        "-b", "--batch-size", type=int, default=BATCH_SIZE,
        help="objects per commit (default: {})".format(BATCH_SIZE))
    parser.add_argument(
        "-p", "--pause", type=float, default=PAUSE,
        help="seconds to sleep between batches (default: no pause)")
    parser.add_argument(
        "--start", type=int, default=0,
        help="position to start at, to resume an interrupted run")
    return parser.parse_args(args)


def setup_site(app, site_id):
    """Makes the site the active site, with a request and the system user
    """
    app = makerequest(app)
    site = app[site_id]
    setSite(site)
    newSecurityManager(None, system)
    return site


def search(catalog_id, query):
    """Searches the catalog without the permission filter

    The resync runs as the system user, whose roles are not part of the
    allowedRolesAndUsers index: a regular search would find nothing.
    """
    catalog = api.get_tool(catalog_id)
    return catalog.unrestrictedSearchResults(**query)


def make_query(portal_types):
    """Returns the catalog query for the portal types
    """
    if not portal_types:
        return {}
    return {"portal_type": portal_types}


def log_to_console():
    """Prints the log messages of the resync, the instance command does
    not configure logging
    """
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    # the root logger may print them as well
    logger.propagate = False


def main(app, args):
    """Entry point of `bin/instance sqlmultiplex_resync`
    """
    options = parse_args(args)
    log_to_console()
    setup_site(app, options.site)
    connector = get_connector()
    if connector is None:
        raise SystemExit("No SQL connection, check the DSN")
    query = make_query(options.portal_types)
    brains = search(options.catalog, query)
    logger.info("Resync: {} objects in {}".format(
        len(brains), options.catalog))
    objects, rows = resync(brains, connector, options.batch_size,
                           options.start, options.pause)
    logger.info("Resync done: {} objects, {} rows".format(objects, rows))
