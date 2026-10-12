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

import logging

from bika.lims import api
from senaite.sqlmultiplex.interfaces import ISQLMultiplexLayer
from zope.i18nmessageid import MessageFactory

PRODUCT_NAME = "senaite.sqlmultiplex"
PROFILE_ID = "profile-{}:default".format(PRODUCT_NAME)
UNINSTALL_PROFILE_ID = "profile-{}:uninstall".format(PRODUCT_NAME)

messageFactory = MessageFactory(PRODUCT_NAME)

logger = logging.getLogger(PRODUCT_NAME)


def initialize(context):
    logger.info("*** Initializing {} Customization package ***"
                .format(PRODUCT_NAME.upper()))


def is_installed():
    """Returns whether the product is installed or not
    """
    request = api.get_request()
    return ISQLMultiplexLayer.providedBy(request)
