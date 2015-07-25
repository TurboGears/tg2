"""Main Controller"""
import tg
from tg import expose, redirect, config, validate, override_template, response, render_template, tmpl_context
from tg import cache, i18n, request
from tg.decorators import paginate, use_custom_format, with_trailing_slash, Decoration, before_render, decode_params
from tg.controllers import TGController
from tg.validation import TGValidationError
from tg._compat import PY3
from tg.render import _get_tg_vars, cached_template
import datetime

if not PY3:
    from tw.forms import TableForm, TextField, CalendarDatePicker, SingleSelectField, TextArea
    from tw.api import WidgetsList

    class MovieForm(TableForm):
        # This WidgetsList is just a container
        class fields(WidgetsList):
            title = TextField()
            year = TextField(size=4, default=1984)
            description = TextArea()

    #then, we create an instance of this form
    base_movie_form = MovieForm("movie_form", action='create')
else:
    base_movie_form = None


import tw2.forms as tw2f
import tw2.core as tw2c
class TW2MovieForm(tw2f.TableForm):
    title = tw2f.TextField(validator=tw2c.Required)
    year = tw2f.TextField(size=4, validator=tw2c.IntValidator)

tw2_movie_form = TW2MovieForm()


class IntValidator(object):
    def to_python(self, value):
        try:
            return int(value)
        except:
            raise TGValidationError('Not a number')


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


class SubClassableController(TGController):
    @expose('genshi:index.html')
    def index(self):
        return {}

    @expose('genshi:index.html')
    def index_override(self):
        return {}

    def before_render_data(remainder, params, output):
        output['parent_value'] = 'PARENT'

    @expose('json')
    @before_render(before_render_data)
    def data(self):
        return {'v':5}

class SubClassingController(SubClassableController):
    @expose(inherit=True)
    def index(self, *args, **kw):
        return super(SubClassingController, self).index(*args, **kw)

    @expose('genshi:genshi_doctype.html', inherit=True)
    def index_override(self, *args, **kw):
        return super(SubClassingController, self).index_override(*args, **kw)

    def before_render_data(remainder, params, output):
        output['child_value'] = 'CHILD'

    @expose(inherit=True)
    @before_render(before_render_data)
    def data(self, *args, **kw):
        return super(SubClassingController, self).data(*args, **kw)

class RootController(TGController):

    j = JsonController()
    sub1 = SubClassableController()
    sub2 = SubClassingController()

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

    @expose('genshi:genshi_form.html')
    def tw2form(self):
        return dict(form=tw2_movie_form)

    @expose('genshi:genshi_foreign.html')
    def foreign(self):
        return {}

    @expose('json')
    @validate(form=base_movie_form)
    def process_form_errors(self, **kwargs):
        #add error messages to the kwargs dictionary and return it
        kwargs['errors'] = request.validation['errors']
        return dict(kwargs)

    @expose()
    @paginate('testdata')
    def paginated_text(self):
        return '''Some Text'''

    @expose('genshi:genshi_paginated.html')
    @expose('json')
    @paginate('testdata', max_items_per_page=20)
    def paginated(self, n):
        return dict(testdata=range(int(n)))

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    def paginate_with_params(self, n):
        url_params = dict(param1='hi', param2='man')
        return dict(testdata=range(int(n)), url_params=url_params)

    @expose('genshi:genshi_paginated.html')
    @paginate('testdata')
    @validate(dict(n=IntValidator()))
    def paginated_validated(self, n):
        return dict(testdata=range(n))

    @expose('genshi:genshi_paginated.html')
    @validate(dict(n=IntValidator()))
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

    @expose('jinja:jinja_noop.jinja')
    def jinja_index(self):
        return {}

    @expose('jinja:jinja_autoload.jinja')
    def jinja_autoload(self):
        return {}

    @expose('jinja:jinja_inherits.jinja')
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

    @expose('jinja:jinja_extensions.jinja')
    def jinja_extensions(self):
        test_autoescape_on = "<b>Test Autoescape On</b>"
        test_autoescape_off = "<b>Autoescape Off</b>"
        return dict(test_autoescape_off=test_autoescape_off,
                test_autoescape_on=test_autoescape_on)

    @expose('jinja:jinja_filters.jinja')
    def jinja_filters(self):
        return {}

    @expose('jinja:jinja_buildins.jinja')
    def jinja_buildins(self):
        return {}

    @expose('jinja:jinja_i18n.jinja')
    def jinja_i18n(self):
        return {}

    @expose('jinja:jinja_i18n.jinja')
    def jinja_i18n_en(self):
        i18n.set_temporary_lang("en")
        return {}

    @expose('jinja:jinja_i18n.jinja')
    def jinja_i18n_de(self):
        i18n.set_temporary_lang("de")
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

    @expose('kajiki:tests.test_stack.rendering.templates.missing')
    def kajiki_missing_template(self):
        return {}

    @expose('kajiki:tests.test_stack.rendering.templates.kajiki_i18n')
    def kajiki_i18n(self):
        return {}

    @expose('kajiki:tests.test_stack.rendering.templates.kajiki_i18n')
    def kajiki_i18n_de(self):
        i18n.set_temporary_lang("de")
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
        try:
            import pylons
        except ImportError:
            frompylons = False

        if frompylons:
            from pylons.templating import render_jinja2
            return render_jinja2('jinja_inherits.jinja')
        else:
            return render_template({}, 'jinja', 'jinja_inherits.jinja')

    @expose()
    def no_template_generator(self):
        def output():
            num = 0
            while num < 5:
                num += 1
                yield str(num).encode('ascii')
        return output()
    
    @expose()
    def genshi_manual_rendering_with_doctype(self, doctype=None):
        response.content_type = 'text/html'
        response.charset = 'utf-8'
        return render_template({}, 'genshi', 'genshi_doctype.html', doctype=doctype)

    @expose('mako:mako_custom_format.mak')
    @expose('genshi:genshi_custom_format.html')
    def multiple_engines(self):
        deco = Decoration.get_decoration(self.multiple_engines)
        used_engine = deco.engines.get('text/html')[0]
        return dict(format=used_engine, status='ok')

    @expose('json')
    def get_tg_vars(self):
        return dict(tg_vars=list(_get_tg_vars().keys()))

    @expose('genshi:index.html')
    def template_caching(self):
        from datetime import datetime
        tmpl_context.now = datetime.utcnow
        return dict(tg_cache={'key':'TEMPLATE_CACHE_TEST',
                              'type':'memory',
                              'expire':'never'})

    @expose('genshi:index.html')
    def template_caching_default_type(self):
        from datetime import datetime
        tmpl_context.now = datetime.utcnow
        return dict(tg_cache={'key':'TEMPLATE_CACHE_TEST2',
                              'expire':'never'})

    @expose('json')
    def template_caching_options(self, **kwargs):
        _cache_options = {}
        class FakeCache(object):
            def get_cache(self, *args, **kwargs):
                _cache_options['args'] = args
                _cache_options['kwargs'] = kwargs
                try:
                    c = cache.get_cache(*args, **kwargs)
                    _cache_options['cls'] = c.namespace.__class__.__name__
                except TypeError:
                    _cache_options['cls'] = 'NoImplementation'
                    c = cache.get_cache(*args, type='memory', **kwargs)
                return c

        tg.cache.kwargs['type'] = 'NoImplementation'
        old_cache = tg.cache
        tg.cache = FakeCache()

        try:
            def render_func(*args, **kw):
                return 'OK'
            cached_template('index.html', render_func, **kwargs)
            return _cache_options
        finally:
            tg.cache = old_cache

    @expose('jsonp', render_params={'callback_param': 'call'})
    def get_jsonp(self, **kwargs):
        return {'value': 5}

    @expose('json')
    def get_json_isodates_default(self, **kwargs):
        return {'date': datetime.datetime.utcnow()}

    @expose('json', render_params={'isodates': True})
    def get_json_isodates_on(self, **kwargs):
        return {'date': datetime.datetime.utcnow()}

    @expose('json', render_params={'isodates': False})
    def get_json_isodates_off(self, **kwargs):
        return {'date': datetime.datetime.utcnow()}

    @expose('json')
    @decode_params('json')
    def echo_json(self, **kwargs):
        return kwargs
