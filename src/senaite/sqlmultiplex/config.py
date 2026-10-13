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

# Environment variable that holds the libpq connection string. Takes
# precedence over the registry record, which is stored in the ZODB in
# plain text.
DSN_ENVIRONMENT_VARIABLE = "SENAITE_SQLMULTIPLEX_DSN"

# Registry records, see controlpanel.ISQLMultiplexControlPanel
REGISTRY_ENABLED = "senaite.sqlmultiplex.enabled"
REGISTRY_CONNECTOR = "senaite.sqlmultiplex.connector"
REGISTRY_DSN = "senaite.sqlmultiplex.dsn"

# Name of the connector utility used when none is configured
DEFAULT_CONNECTOR = "postgresql"
