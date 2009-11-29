from tg import expose, redirect, config, validate
from tg.decorators import paginate, use_custom_format
from tg.controllers import RoutingController
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

class RoutingtestController(RoutingController):
    # These actions are identical to those used by
    # tg/test_stack/rendering/controllers/root.py.

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
