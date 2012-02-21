"""Main Controller"""

from tg import expose, redirect, config, validate, override_template, response
from tg.decorators import paginate, use_custom_format, with_trailing_slash
from tg.render import render
from tg.controllers import TGController
from tw.forms import TableForm, TextField, CalendarDatePicker, SingleSelectField, TextArea
from tw.api import WidgetsList
from formencode import validators

class MovieForm(TableForm):
    # This WidgetsList is just a container
    class fields(WidgetsList):
        title = TextField()
        year = TextField(size=4, default=1984)
        description = TextArea()

#then, we create an instance of this form
base_movie_form = MovieForm("movie_form", action='create')


class GoodJsonObject(object):

    def __json__(self):
        return {'Json':'Rocks'}

class BadJsonObject(object):
    pass


class JsonController(TGController):

    @expose('json')
    def json(self):
        return dict(a='hello world', b=True)

    @expose('json', exclude_names=["b"])
    def excluded_b(self):
        return dict(a="visible", b="invisible")

    @expose('json')
    @expose('genshi:test', content_type='application/xml')
    def xml_or_json(self):
        return dict(name="John Carter", title='officer', status='missing')

    @expose('json')
    def json_with_object(self):
        return dict(obj=GoodJsonObject())

    @expose('json')
    def json_with_bad_object(self):
        return dict(obj=BadJsonObject())


class RootController(TGController):

    j = JsonController()

    @expose('genshi:index.html')
    def index(self):
        return {}

    @expose('genshi:genshi_doctype.html')
    def auto_doctype(self):
        return {}

    @expose('genshi:genshi_doctype.html', content_type='text/html')
    def auto_doctype_html(self):
        return {}

    @expose('genshi:genshi_doctype.html', content_type='application/xhtml+xml')
    def auto_doctype_xhtml(self):
        return {}

    @expose('genshi:genshi_doctype.html', render_params=dict(doctype=None))
    def explicit_no_doctype(self):
        return {}

    @expose('genshi:genshi_doctype.html', render_params=dict(doctype='html'))
    def explicit_doctype_html(self):
        return {}

    @expose('genshi:genshi_doctype.html', render_params=dict(doctype='xhtml'))
    def explicit_doctype_xhtml(self):
        return {}

    @expose('genshi:genshi_form.html')
    def form(self):
        return dict(form=base_movie_form)

    @expose('genshi:genshi_foreign.html')
    def foreign(self):
        return {}

    @expose('json')
    @validate(form=base_movie_form)
    def process_form_errors(self, **kwargs):
        #add error messages to the kwargs dictionary and return it
        kwargs['errors'] = pylons.tmpl_context.form_errors
        return dict(kwargs)

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    def paginated(self, n):
        return dict(testdata=range(int(n)))

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    def paginate_with_params(self, n):
        url_params = dict(param1='hi', param2='man')
        return dict(testdata=range(int(n)), url_params=url_params)

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    @validate(dict(n=validators.Int()))
    def paginated_validated(self, n):
        return dict(testdata=range(n))

    @expose('genshi:genshi_paginated.html')
    @validate(dict(n=validators.Int()))
    @paginate('testdata')
    def validated_paginated(self, n):
        return dict(testdata=range(n))

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata', use_prefix=True)
    @paginate('testdata2', use_prefix=True)
    def multiple_paginators(self, n):
        n = int(n)
        return dict(testdata=range(n), testdata2=range(n+100, n+100+n))

    @expose('genshi:genshi_inherits.html')
    def genshi_inherits(self):
        return {}

    @expose('genshi:genshi_inherits_sub.html')
    def genshi_inherits_sub(self):
        return {}

    @expose('genshi:sub/frombottom.html')
    def genshi_inherits_sub_from_bottom(self):
        return {}

    @expose('jinja:jinja_noop.html')
    def jinja_index(self):
        return {}

    @expose('jinja:jinja_inherits.html')
    def jinja_inherits(self):
        return {}

    @expose('jinja:tests.test_stack.rendering.templates.jinja_noop')
    def jinja_dotted(self):
        return {}

    @expose('jinja:tests.test_stack.rendering.templates.jinja_inherits_dotted')
    def jinja_inherits_dotted(self):
        return {}

    @expose('jinja:tests.test_stack.rendering.templates.jinja_inherits')
    def jinja_inherits_mixed(self):
        return {}

    @expose('jinja:jinja_extensions.html')
    def jinja_extensions(self):
        test_autoescape_on = "<b>Test Autoescape On</b>"
        test_autoescape_off = "<b>Autoescape Off</b>"
        return dict(test_autoescape_off=test_autoescape_off,
                test_autoescape_on=test_autoescape_on)

    @expose('jinja:jinja_filters.html')
    def jinja_filters(self):
        return {}

    @expose('jinja:jinja_buildins.html')
    def jinja_buildins(self):
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

    @expose('chameleon_genshi:tests.test_stack.rendering.templates.index')
    def chameleon_index_dotted(self):
        return {}

    @expose('kajiki:tests.test_stack.rendering.templates.index')
    def kajiki_index_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.index')
    def index_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.genshi_inherits')
    def genshi_inherits_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.genshi_inherits_sub_dotted')
    def genshi_inherits_sub_dotted(self):
        return {}

    @expose('genshi:tests.test_stack.rendering.templates.sub.frombottom_dotted')
    def genshi_inherits_sub_dotted_from_bottom(self):
        return {}

    @expose('mako:tests.test_stack.rendering.templates.mako_noop')
    def mako_index_dotted(self):
        return {}

    @expose('mako:tests.test_stack.rendering.templates.mako_inherits_dotted')
    def mako_inherits_dotted(self):
        return {}

    @expose('json')
    @expose('genshi:index.html')
    def html_and_json(self):
        return {}

    @expose('json', custom_format='json')
    @expose('mako:mako_custom_format.mak', content_type='text/xml', custom_format='xml')
    @expose('genshi:genshi_custom_format.html', content_type='text/html', custom_format='html')
    def custom_format(self, format='default'):
        if format != 'default':
            use_custom_format(self.custom_format, format)
            return dict(format=format, status="ok")
        else:
            return 'OK'

    @expose("genshi:tests.non_overridden")
    def template_override(self, override=False):
        if override:
            override_template(self.template_override, "genshi:tests.overridden")
        return dict()

    @with_trailing_slash
    @expose("genshi:tests.non_overridden")
    def template_override_wts(self, override=False):
        if override:
            override_template(self.template_override_wts, "genshi:tests.overridden")
        return dict()

    @expose(content_type='text/javascript')
    def template_override_content_type(self, override=False):
        if override:
            override_template(self.template_override_content_type, "mako:tests.overridden_js")
            return dict()
        else:
            return "alert('Not overridden')"

    @expose('mako:mako_custom_format.mak', content_type='text/xml')
    @expose('genshi:genshi_custom_format.html', content_type='text/html')
    def template_override_multiple_content_type(self, override=False):
        if override:
            override_template(self.template_override_multiple_content_type, "mako:mako_noop.mak")
        return dict(format='something', status="ok")

    @expose()
    def jinja2_manual_rendering(self, frompylons=False):
        if frompylons:
            from pylons.templating import render_jinja2
            return render_jinja2('jinja_inherits.html')
        else:
            return render({}, 'jinja', 'jinja_inherits.html')

    @expose()
    def genshi_manual_rendering_with_doctype(self, doctype=None):
        response.content_type = 'text/html'
        response.charset = 'utf-8'
        return render({}, 'genshi', 'genshi_doctype.html', doctype=doctype)

