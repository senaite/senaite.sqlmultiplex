from senaite.sqlmultiplex import PRODUCT_NAME
from senaite.sqlmultiplex.config import NON_SUPPORTED_FIELD_NAMES
from senaite.sqlmultiplex.config import NON_SUPPORTED_FIELD_TYPES
from senaite.sqlmultiplex.config import NON_SUPPORTED_FIELDS_BY_PORTAL_TYPE
from senaite.sqlmultiplex.config import OTHER_FIELDS

from bika.lims import api


def get_multiplexed_types():
    """Returns the list of portal types to be multiplexed
    """
    reg_id = "{}.content_types".format(PRODUCT_NAME)
    return api.get_registry_record(reg_id, [])


def get_connector_type():
    """Returns the type of SQL connector to use
    """
    reg_id = "{}.db_type".format(PRODUCT_NAME)
    return api.get_registry_record(reg_id)


def raise_errors():
    """Returns whether SQL errors must be rised instead of failig
    silenty
    """
    reg_id = "{}.raise_errors".format(PRODUCT_NAME)
    return api.get_registry_record(reg_id)


def supports_multiplex(obj):
    """Returns whether the obj supports multiplex
    """
    if api.get_portal_type(obj) in get_multiplexed_types():
        return not api.is_temporary(obj)
    return False


def get_supported_fields(obj):
    """Returns the fields from the objects to keep mapped against the SQL
    database
    """
    portal_type = api.get_portal_type(obj)
    if portal_type not in get_multiplexed_types():
        return []

    fields = []
    obj_fields = api.get_fields(obj).values()
    skip = dict(NON_SUPPORTED_FIELDS_BY_PORTAL_TYPE).get(portal_type, [])
    for field in obj_fields:
        # skip non-supported fields by name
        if field.getName() in skip:
            continue
        if field.getName() in NON_SUPPORTED_FIELD_NAMES:
            continue
        # skip non-supported fields by type
        if field.type in NON_SUPPORTED_FIELD_TYPES:
            continue

        fields.append(field)

    # append other fields/funcs/attrs
    other = dict(OTHER_FIELDS).get(portal_type, [])
    fields.extend(other)
    return fields
