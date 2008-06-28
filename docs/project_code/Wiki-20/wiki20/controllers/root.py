"""Main Controller"""
from wiki20.lib.base import BaseController
from tg import expose, flash
from pylons.i18n import ugettext as _
#from tg import redirect, validate
from wiki20.model import DBSession, metadata
#from dbsprockets.dbmechanic.frameworks.tg2 import DBMechanic
#from dbsprockets.saprovider import SAProvider
from wiki20.model.page import Page

class RootController(BaseController):
    #admin = DBMechanic(SAProvider(metadata), '/admin')

    @expose('wiki20.templates.page')
    def index(self, pagename="FrontPage"):
        page = DBSession.query(Page).filter_by(pagename=pagename).one()
        return dict(wikipage=page)

    @expose('wiki20.templates.about')
    def about(self):
        return dict()
