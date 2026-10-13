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

from senaite.core.interfaces import ISenaiteCore
from senaite.lims.interfaces import ISenaiteLIMS
from zope.interface import Attribute
from zope.interface import Interface


class ISQLMultiplexLayer(ISenaiteCore, ISenaiteLIMS):
    """Zope 3 browser Layer interface specific for senaite.sqlmultiplex
    This interface is referred in profiles/default/browserlayer.xml.
    All views and viewlets register against this layer will appear in the site
    only when the add-on installer has been run.
    """


class ISQLRow(Interface):
    """Adapter that maps a content object to one row of a SQL table

    Register it as a (named) adapter for the content interface. Objects
    without an adapter are not mirrored. Several named adapters for the
    same object write into several tables.
    """

    table = Attribute("Name of the SQL table")

    primary_key = Attribute("Name of the primary key column")

    columns = Attribute(
        "Ordered sequence of (column name, SQL type) tuples, including "
        "the primary key column")

    def applies():
        """Returns whether the object belongs into the table

        If not, an existing row of the object is removed. This is the
        place for filters like "published samples only".
        """

    def key():
        """Returns the primary key value of the object
        """

    def values():
        """Returns a dict of column name -> value for the row
        """


class ISQLConnector(Interface):
    """Writes rows into a SQL database

    Registered as a named global utility and therefore shared by all
    threads. Implementations must keep one connection per thread, so
    that one ZODB transaction maps to exactly one database transaction.
    Nothing is committed before commit() is called.
    """

    def is_active():
        """Returns whether the current thread has a usable connection
        """

    def upsert(row):
        """Inserts or updates the row of the given ISQLRow

        Creates the table and missing columns if needed. Returns False
        if the database rejected the row, without affecting the rows
        written before in the same transaction.
        """

    def delete(row):
        """Removes the row of the given ISQLRow, if any

        Returns False if the database rejected the statement.
        """

    def commit():
        """Commits the transaction of the current thread
        """

    def rollback():
        """Rolls back the transaction of the current thread
        """
