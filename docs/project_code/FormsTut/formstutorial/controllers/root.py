"""Main Controller"""
from formstutorial.lib.base import BaseController
from tg import expose, flash
import pylons
from pylons.i18n import ugettext as _
#from tg import redirect, validate
#from formstutorial.model import DBSession, metadata
#from dbsprockets.dbmechanic.frameworks.tg2 import DBMechanic
#from dbsprockets.saprovider import SAProvider

from tw.forms import TableForm, TextField, CalendarDatePicker, SingleSelectField, TextArea
from tw.api import WidgetsList

class MovieForm(TableForm):
    # This WidgetsList is just a container
    class fields(WidgetsList):
        title = TextField()
        year = TextField(size=4)
        release_date = CalendarDatePicker()
        generachoices = ((1,"Action & Adventure"),
                         (2,"Animation"),
                         (3,"Comedy"),
                         (4,"Documentary"),
                         (5,"Drama"),
                         (6,"Sci-Fi & Fantasy"))
        genera = SingleSelectField(options=generachoices)
        description = TextArea()

#then, we create an instance of this form
create_movie_form = MovieForm("create_movie_form", action='create')

class RootController(BaseController):
    #admin = DBMechanic(SAProvider(metadata), '/admin')

    @expose('formstutorial.templates.index')
    def index(self):
        return dict(page='index')

    @expose('formstutorial.templates.about')
    def about(self):
        return dict(page='about')

    @expose("formstutorial.templates.new_form")
    def new_form(self, **kw):
        """Form to add new record"""
        # Passing the form in the return dict is no longer kosher, you can
        # set pylons.c.form instead and use c.form in your template
        # (remember to 'import pylons' too)
        pylons.c.form = create_movie_form
        return dict(page='Movie')

