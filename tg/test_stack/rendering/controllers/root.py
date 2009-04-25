"""Main Controller"""

from tg import expose, redirect, config, validate
from tg.decorators import paginate, use_custom_format
from tg.controllers import TGController
from tw.forms import TableForm, TextField, CalendarDatePicker, SingleSelectField, TextArea
from tw.api import WidgetsList
from formencode import validators

class MovieForm(TableForm):
    # This WidgetsList is just a container
    class fields(WidgetsList):
        title = TextField()
        year = TextField(size=4)
        description = TextArea()

#then, we create an instance of this form
base_movie_form = MovieForm("movie_form", action='create')

class RootController(TGController):
    @expose('genshi:index.html')
    def index(self):
        return {}

    @expose('genshi:genshi_form.html')
    def form(self):
        return dict(form=base_movie_form)

    @expose('json')
    @validate(form=base_movie_form)
    def process_form_errors(self, **kwargs):
        #add error messages to the kwargs dictionary and return it
        kwargs['errors'] = pylons.tmpl_context.form_errors
        return dict(kwargs)

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    def paginated(self):
        return dict(testdata=range(42))

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    @validate({'i':validators.Int()})
    def paginated_validated(self, i=None):
        return dict(testdata=range(42))
    
    @expose('genshi:genshi_inherits.html')
    def genshi_inherits(self):
        return {}

    @expose('jinja:jinja_noop.html')
    def jinja_index(self):
        return {}

    @expose('jinja:jinja_inherits.html')
    def jinja_inherits(self):
        return {}

    @expose('chameleon_genshi:index.html')
    def chameleon_genshi_index(self):
        return {}

    @expose('chameleon_genshi:genshi_inherits.html')
    def chameleon_genshi_inherits(self):
        return {}

    @expose('mako:mako_noop.mak')
    def mako_index(self):
        return {}

    @expose('mako:mako_inherits.mak')
    def mako_inherits(self):
        return {}

    @expose('chameleon_genshi:tg.test_stack.rendering.templates.index')
    def chameleon_index_dotted(self):
        return {}

    @expose('genshi:tg.test_stack.rendering.templates.index')
    def index_dotted(self):
        return {}

    @expose('genshi:tg.test_stack.rendering.templates.genshi_inherits')
    def genshi_inherits_dotted(self):
        return {}

    @expose('mako:tg.test_stack.rendering.templates.mako_noop')
    def mako_index_dotted(self):
        return {}

    @expose('mako:tg.test_stack.rendering.templates.mako_inherits_dotted')
    def mako_inherits_dotted(self):
        return {}

    @expose('json', custom_format='json')
    @expose('mako:mako_custom_format.mak', content_type='text/xml', custom_format='xml')
    @expose('genshi:genshi_custom_format.html', content_type='text/html', custom_format='html')
    def custom_format(self, format):
        use_custom_format(self.custom_format, format)
        return dict(format=format, status="ok")
