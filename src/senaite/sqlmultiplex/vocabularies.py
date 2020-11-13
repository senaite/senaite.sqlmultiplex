
from bika.lims import api
from senaite.sqlmultiplex.config import NON_SUPPORTED_TYPES
from zope.interface import implementer
from zope.schema.interfaces import IVocabularyFactory
from zope.schema.vocabulary import SimpleTerm
from zope.schema.vocabulary import SimpleVocabulary


@implementer(IVocabularyFactory)
class PortalTypesVocabulary(object):

    def __call__(self, context):
        portal_state = api.get_view("plone_portal_state")
        content_types = portal_state.friendly_types()
        # filter out non supported types
        content_types = filter(
            lambda pt: pt not in NON_SUPPORTED_TYPES, content_types)
        items = [
            SimpleTerm(item, item, item)
            for item in content_types
        ]
        return SimpleVocabulary(items)


PortalTypesVocabularyFactory = PortalTypesVocabulary()
