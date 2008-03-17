"""Main Controller"""
from TGTest.lib.base import BaseController
from tg import expose, flash
from pylons.i18n import ugettext as _
#from tg import redirect, validate
#from TGTest.model import DBSession

class RootController(BaseController):

    @expose('TGTest.templates.index')
    def index(self):
        from datetime import datetime
        flash(_("Your application is now running"))
        return dict(now=datetime.now())
