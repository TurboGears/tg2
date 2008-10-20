"""Main Controller"""
from wiki20.lib.base import BaseController
from tg import expose, flash
from pylons.i18n import ugettext as _
import tg
from tg import redirect, validate
from wiki20.model import DBSession, metadata
#from dbsprockets.dbmechanic.frameworks.tg2 import DBMechanic
#from dbsprockets.saprovider import SAProvider
from wiki20.model.page import Page
import re
from docutils.core import publish_parts

wikiwords = re.compile(r"\\b([A-Z]\\w+[A-Z]+\\w+)")

class RootController(BaseController):
    #admin = DBMechanic(SAProvider(metadata), '/admin')

    @expose('wiki20.templates.page')
    def default(self, pagename="FrontPage"):
        page = DBSession.query(Page).filter_by(pagename=pagename).one()
        content = publish_parts(page.data, writer_name="html")["html_body"]
        root = tg.url('/')
        content = wikiwords.sub(r'<a href="%s\\1">\\1</a>' % root, content)
        return dict(content=content, wikipage=page)

    @expose(template="wiki20.templates.edit")
    def edit(self, pagename):
        page = DBSession.query(Page).filter_by(pagename=pagename).one()
        return dict(wikipage=page)

    @expose('wiki20.templates.about')
    def about(self):
        return dict()

    @expose()
    def save(self, pagename, data, submit):
        page = DBSession.query(Page).filter_by(pagename=pagename).one()
        page.data = data
        DBSession.commit() # Tells database to commit changes permanently
        redirect("/" + pagename)