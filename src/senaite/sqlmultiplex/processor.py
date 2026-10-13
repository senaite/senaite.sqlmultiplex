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

from bika.lims import api
from Products.CMFCore.interfaces import IPortalCatalogQueueProcessor
from senaite.sqlmultiplex import logger
from senaite.sqlmultiplex.config import DEFAULT_CONNECTOR
from senaite.sqlmultiplex.config import REGISTRY_CONNECTOR
from senaite.sqlmultiplex.config import REGISTRY_ENABLED
from senaite.sqlmultiplex.interfaces import ISQLConnector
from senaite.sqlmultiplex.interfaces import ISQLRow
from zope.component import getAdapters
from zope.component import queryUtility
from zope.interface import implementer


def is_enabled():
    """Returns whether the multiplexer is enabled

    The registry record only exists when the add-on is installed.
    """
    return api.get_registry_record(REGISTRY_ENABLED, default=False) is True


def query_connector():
    """Returns the configured connector utility or None
    """
    name = api.get_registry_record(REGISTRY_CONNECTOR) or DEFAULT_CONNECTOR
    return queryUtility(ISQLConnector, name=name)


def get_connector():
    """Returns the configured connector, or None if it has no usable
    connection for the current thread
    """
    connector = query_connector()
    if connector is None or not connector.is_active():
        return None
    return connector


def get_rows(obj):
    """Returns the ISQLRow adapters of the object

    An adapter that fails to construct is logged, see write.
    """
    if not api.is_object(obj) or api.is_temporary(obj):
        return []
    try:
        return [row for name, row in getAdapters((obj, ), ISQLRow)]
    except Exception:
        logger.exception("Skipping the rows of {}".format(
            api.get_path(obj)))
        return []


def write(connector, row):
    """Writes the row, or removes it if the object no longer applies

    Returns False if the row could not be written.
    """
    # The row adapters are code of other add-ons and read arbitrary
    # object data. Whatever they raise must not reach SENAITE: a bug in
    # an adapter or bad data in one object would otherwise stop the lab
    # from saving. The values are read before the database is touched,
    # so skipping the row leaves the transaction clean.
    try:
        if row.applies():
            return connector.upsert(row)
        return connector.delete(row)
    except Exception:
        logger.exception("Skipping row of {} for {}".format(
            row.__class__.__name__, get_path(row)))
        return False


def delete(connector, row):
    """Removes the row, see write for the error handling
    """
    try:
        return connector.delete(row)
    except Exception:
        logger.exception("Skipping removal of {} for {}".format(
            row.__class__.__name__, get_path(row)))
        return False


def get_path(row):
    """Returns the path of the adapted object, for log messages
    """
    context = getattr(row, "context", None)
    if context is None:
        return repr(row)
    return api.get_path(context)


@implementer(IPortalCatalogQueueProcessor)
class SQLMultiplexProcessor(object):
    """Mirrors objects with an ISQLRow adapter into a SQL database

    Called by the indexing queue of CMFCore: index, reindex and unindex
    in the before commit hook of the ZODB transaction (or earlier, when
    a catalog query flushes the queue), commit after the ZODB commit
    succeeded, abort when it failed. Rows are therefore committed if
    and only if the ZODB transaction is.
    """

    def index(self, obj, attributes=None):
        rows = self.get_rows(obj)
        if not rows:
            return
        connector = get_connector()
        if connector is None:
            return
        for row in rows:
            write(connector, row)

    def reindex(self, obj, attributes=None, update_metadata=1):
        self.index(obj, attributes=attributes)

    def unindex(self, obj):
        rows = self.get_rows(obj)
        if not rows:
            return
        connector = get_connector()
        if connector is None:
            return
        for row in rows:
            delete(connector, row)

    def get_rows(self, obj):
        if not is_enabled():
            return []
        return get_rows(obj)

    def begin(self):
        pass

    # commit and abort do not check is_active(): that would open a
    # connection in threads that have not written anything

    def commit(self):
        if not is_enabled():
            return
        connector = query_connector()
        if connector is not None:
            connector.commit()

    def abort(self):
        if not is_enabled():
            return
        connector = query_connector()
        if connector is not None:
            connector.rollback()
