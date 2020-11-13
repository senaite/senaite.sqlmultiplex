from senaite.core.interfaces import ISenaiteCore
from senaite.lims.interfaces import ISenaiteLIMS


class ISQLMultiplexLayer(ISenaiteCore, ISenaiteLIMS):
    """Zope 3 browser Layer interface specific for senaite.sqlmultiplex
    This interface is referred in profiles/default/browserlayer.xml.
    All views and viewlets register against this layer will appear in the site
    only when the add-on installer has been run.
    """
