
from plone.app.registry.browser.controlpanel import ControlPanelFormWrapper
from plone.app.registry.browser.controlpanel import RegistryEditForm
from plone.z3cform import layout
from senaite.sqlmultiplex import messageFactory as _
from zope import schema
from zope.interface import Interface
from z3c.form.browser.checkbox import CheckBoxFieldWidget


class ISQLMultiplexControlPanel(Interface):
    """Control panel Settings
    """

    host = schema.TextLine(
        title=_(u"Server"),
        default=u"localhost",
        required=False,
    )

    port = schema.Int(
        title=_(u"Port"),
        min=0,
        max=65535,
        default=3306,
        required=False,
    )

    database = schema.TextLine(
        title=_(u"Database name"),
        default=u"senaite",
        required=False,
    )

    user = schema.TextLine(
        title=_(u"Database user"),
        default=u"root",
        required=False,
    )

    password = schema.Password(
        title=_(u"Database user password"),
        default=u"",
        required=False,
    )

    content_types = schema.List(
        title=_(u"Tables"),
        required=False,
        value_type=schema.Choice(
            source="senaite.sqlmultiplex.vocabularies.portal_types"
        )
    )


class SQLMultiplexControlPanelForm(RegistryEditForm):
    schema = ISQLMultiplexControlPanel
    schema_prefix = "senaite.sqlmultiplex"
    label = _("SQL Multiplex Settings")


SQLMultiplexControlPanel = layout.wrap_form(SQLMultiplexControlPanelForm,
                                            ControlPanelFormWrapper)
