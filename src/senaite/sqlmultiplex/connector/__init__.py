# -*- coding: utf-8 -*-
import json

from senaite.core.supermodel import SuperModel
from senaite.sqlmultiplex import PRODUCT_NAME

from bika.lims import api


class SqlConnector(object):

    @property
    def host(self):
        key = "{}.host".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def port(self):
        key = "{}.port".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def dbname(self):
        key = "{}.database".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def username(self):
        key = "{}.user".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    @property
    def password(self):
        key = "{}.password".format(PRODUCT_NAME)
        return api.get_registry_record(key)

    def get_info(self, obj, attributes=None):
        """Returns a dict with the information of the object, suitable for SQL
        operations
        """
        if attributes is None:
            attributes = []

        info = {}
        sm = SuperModel(obj)

        # Generate a dict with the requested attributes only
        for name in attributes:
            info[name] = sm.stringify(sm.get(name, ""))

        # Sanitize the dict values to hold values suitable for SQL
        for k in info.keys():
            v = info.get(k)
            if isinstance(v, (list, tuple, dict)):
                info.update({k: json.dumps(v)})

        return info
