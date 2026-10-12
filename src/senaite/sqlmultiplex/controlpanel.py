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

from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.z3cform import layout
from senaite.sqlmultiplex import messageFactory as _
from senaite.sqlmultiplex.config import DEFAULT_CONNECTOR
from zope import schema
from zope.interface import Interface


class ISQLMultiplexControlPanel(Interface):
    """Control panel Settings
    """

    enabled = schema.Bool(
        title=_(u"Enabled"),
        description=_(
            u"Mirror objects with a SQL row adapter into the database"),
        default=False,
        required=False,
    )

    connector = schema.TextLine(
        title=_(u"Connector"),
        description=_(u"Name of the SQL connector utility"),
        default=DEFAULT_CONNECTOR.decode("utf-8"),
        required=False,
    )

    dsn = schema.TextLine(
        title=_(u"Connection string"),
        description=_(
            u"libpq connection string, e.g. "
            u"'host=localhost dbname=senaite user=senaite password=...'. "
            u"Stored in plain text in the database. Prefer the environment "
            u"variable SENAITE_SQLMULTIPLEX_DSN, which takes precedence."),
        default=u"",
        required=False,
    )


class SQLMultiplexControlPanelForm(RegistryEditForm):
    schema = ISQLMultiplexControlPanel
    schema_prefix = "senaite.sqlmultiplex"
    label = _("SQL Multiplex Settings")


SQLMultiplexControlPanel = layout.wrap_form(SQLMultiplexControlPanelForm,
                                            ControlPanelFormWrapper)
