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
from senaite.sqlmultiplex.interfaces import ISQLRow
from zope.interface import implementer


@implementer(ISQLRow)
class SQLRow(object):
    """Base class for ISQLRow adapters

    Subclasses set `table` and `columns` and provide one getter per
    column, named `get_<column>`, that returns the value of that column
    for the adapted object:

        class SampleRow(SQLRow):
            table = "sample"
            columns = (
                ("uid", "varchar(32)"),
                ("sample_id", "text"),
            )

            def get_sample_id(self):
                return api.get_id(self.context)
    """

    table = None
    primary_key = "uid"
    columns = (
        ("uid", "varchar(32)"),
    )

    def __init__(self, context):
        self.context = context

    def applies(self):
        return True

    def key(self):
        return self.get_value(self.primary_key)

    def get_value(self, column):
        """Returns the value of a single column
        """
        getter = getattr(self, "get_{}".format(column), None)
        if getter is None:
            raise NotImplementedError(
                "{} has no getter for column '{}'".format(
                    self.__class__.__name__, column))
        return getter()

    def values(self):
        return dict(
            (name, self.get_value(name)) for name, sql_type in self.columns)

    def get_uid(self):
        return api.get_uid(self.context)
