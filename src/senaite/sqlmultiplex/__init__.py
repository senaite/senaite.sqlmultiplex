
import logging

from .interfaces import ISQLMultiplexLayer
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
    from bika.lims import api
    request = api.get_request()
    return ISQLMultiplexLayer.providedBy(request)


def check_installed(func):
    """Decorator that executes the function only if the product is installed
    """
    def wrapper(*args, **kwargs):
        if is_installed():
            return func(*args, **kwargs)
    return wrapper
