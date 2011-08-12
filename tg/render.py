from urllib import quote_plus

from pylons.configuration import config
from paste.deploy.converters import asbool
from pylons import (app_globals, session, tmpl_context, request,
                    response, templating)

try:
    from repoze.what import predicates
except ImportError:
    predicates = []

from webhelpers.html import literal

import tg
from tg.configuration import Bunch

from webhelpers.html import literal

#monkey patch alert!
import pylons
def my_pylons_globals():
    """Create and return a dictionary of global Pylons variables

    Render functions should call this to retrieve a list of global
    Pylons variables that should be included in the global template
    namespace if possible.

    Pylons variables that are returned in the dictionary:
        ``c``, ``g``, ``h``, ``_``, ``N_``, config, request, response,
        translator, ungettext, ``url``

    If SessionMiddleware is being used, ``session`` will also be
    available in the template namespace.

    """

    conf = pylons.config._current_obj()
    c = pylons.tmpl_context._current_obj()
    g = conf.get('pylons.app_globals') or conf['pylons.g']

    try:
        h = conf['package'].lib.helpers

    except (AttributeError, KeyError):
        h = Bunch()

    pylons_vars = dict(
        c=c,
        tmpl_context=c,
        config=conf,
        app_globals=g,
        g=g,
        h = h,
        #h=conf.get('pylons.h') or pylons.h._current_obj(),
        request=pylons.request._current_obj(),
        response=pylons.response._current_obj(),
        url=pylons.url._current_obj(),
        translator=pylons.translator._current_obj(),
        ungettext=pylons.i18n.ungettext,
        _=pylons.i18n._,
        N_=pylons.i18n.N_
    )

    # If the session was overridden to be None, don't populate the session var
    econf = pylons.config['pylons.environ_config']
    if 'beaker.session' in pylons.request.environ or \
        ('session' in econf and econf['session'] in pylons.request.environ):
        pylons_vars['session'] = pylons.session._current_obj()
    templating.log.debug("Created render namespace with pylons vars: %s", pylons_vars)
    return pylons_vars

templating.pylons_globals = my_pylons_globals
#end monkeying around

class MissingRendererError(Exception):
    def __init__(self, template_engine):
        Exception.__init__(self,
            ("The renderer for '%(template_engine)s' templates is missing. "
            "Try adding the following line in you app_cfg.py:\n"
            "\"base_config.renderers.append('%(template_engine)s')\"") % dict(
            template_engine=template_engine))
        self.template_engine = template_engine


class DeprecatedFlashVariable(object):
    def __init__(self, callable, msg):
        self.callable = callable
        self.msg = msg

    def __unicode__(self):
        import warnings
        warnings.warn(self.msg, DeprecationWarning, 2)
        return unicode(self.callable())

    def __nonzero__(self):
        import warnings
        warnings.warn(self.msg, DeprecationWarning, 2)
        return bool(self.callable())


def _get_tg_vars():
    """Create a Bunch of variables that should be available in all templates.

    These variables are:

    WARNING: This function should not be called from outside of the render()
    code.  Please consider this function as private.

    quote_plus
        the urllib quote_plus function
    url
        the turbogears.url function for creating flexible URLs
    identity
        the current visitor's identity information
    session
        the current beaker.session if the session_filter.on it set
        in the app.cfg configuration file. If it is not set then session
        will be None.
    locale
        the default locale
    inputs
        input values from a form
    errors
        validation errors
    request
        the WebOb Request Object
    config
        the app's config object
    auth_stack_enabled
        A boolean that determines if the auth stack is present in the environment
    predicates
        The :mod:`repoze.what.predicates` module.

    """
    # TODO: Implement user_agent and other missing features.
    tg_vars = Bunch(
        config = tg.config,
        flash_obj = tg.flash,
        flash = DeprecatedFlashVariable(
            lambda: tg.flash.message,
            "flash is deprecated, please use flash_obj.message instead "
            "or use the new flash_obj.render() method"
            ),
        flash_status = DeprecatedFlashVariable(
            lambda: 'status_' + tg.flash.status,
            "flash_status is deprecated, please use flash_obj.status instead "
            "or use the new flash_obj.render() method"
            ),
        quote_plus = quote_plus,
        url = tg.url,
        # this will be None if no identity
        identity = request.environ.get('repoze.who.identity'),
        session = session,
        locale = tg.request.accept_language.best_matches(),
        errors = getattr(tmpl_context, "form_errors", {}),
        inputs = getattr(tmpl_context, "form_values", {}),
        request = tg.request,
        auth_stack_enabled = 'repoze.who.plugins' in tg.request.environ,
        predicates = predicates,
        )

    try:
        h = config.package.lib.helpers
    except AttributeError, ImportError:
        h = Bunch()

    root_vars = Bunch(
        c = tmpl_context,
        tmpl_context = tmpl_context,
        response = response,
        request = request,
        url = tg.url,
        helpers = h,
        h = h,
        tg = tg_vars
        )
    # Allow users to provide a callable that defines extra vars to be
    # added to the template namespace
    variable_provider = config.get('variable_provider', None)
    if variable_provider:
        root_vars.update(variable_provider())
    return root_vars


def render(template_vars, template_engine=None, template_name=None, **kwargs):

    render_function = None
    if template_engine is not None:
        # the engine was defined in the @expose()
        render_function = config['render_functions'].get(template_engine)

        if render_function is None:
            # engine was forced in @expose() but is not present in the
            # engine list, warn developer
            raise MissingRendererError(template_engine)

    if not template_vars:
        template_vars={}

    if template_engine != "json" and template_engine != 'amf':
        # Get the extra vars, and merge in the vars from the controller
        tg_vars = _get_tg_vars()
        tg_vars.update(template_vars)
        template_vars = tg_vars

    if not render_function:
        # getting the default renderer, if no engine was defined in @expose()
        render_function = config['render_functions'][config['default_renderer']]

    return render_function(template_name, template_vars, **kwargs)


class RenderChameleonGenshi(object):
    """Singleton that can be called as the Chameleon-Genshi render function."""

    format_for_content_type = {
        'text/plain': 'text',
        'text/css': 'text',
        'text/html': 'xml',
        'text/xml': 'xml',
        'application/xml': 'xml',
        'application/xhtml+xml': 'xml',
        'application/atom+xml': 'xml',
        'application/rss+xml': 'xml',
        'application/soap+xml': 'xml',
        'image/svg+xml': 'xml'}

    def __init__(self, loader):
        self.load_template = loader.load

    def __call__(self, template_name, template_vars, **kwargs):
        """Render the template_vars with the Chameleon-Genshi template."""

        # Gets template format from content type or from config options
        format = kwargs.get('format')
        if not format:
            format = self.format_for_content_type.get(response.content_type)
            if not format:
                format = config.get('templating.chameleon.genshi.format')
                if not format:
                    format = config.get('templating.genshi.method')
                    if not format or format not in ('xml', 'text'):
                        format = 'xml'

        def render_template():
            template_vars.update(my_pylons_globals())
            template = self.load_template(template_name, format=format)
            return literal(template.render(**template_vars))

        return templating.cached_template(
            template_name, render_template,
            ns_options=('doctype', 'method'), **kwargs)


class RenderGenshi(object):
    """Singleton that can be called as the Genshi render function."""

    genshi_functions = {} # auxiliary Genshi functions loaded on demand

    doctypes_for_methods = {
        'html': 'html-transitional',
        'xhtml': 'xhtml-transitional'}

    doctypes_for_content_type = {
        'text/html': ('html', 'html-transitional',
        'html-frameset', 'html5',
        'xhtml', 'xhtml-strict',
        'xhtml-transitional', 'xhtml-frameset'),
        'application/xhtml+xml': ('xhtml', 'xhtml-strict',
        'xhtml-transitional',
        'xhtml-frameset', 'xhtml11'),
        'image/svg+xml': ('svg', 'svg-full', 'svg-basic', 'svg-tiny')
        }

    methods_for_content_type = {
        'text/plain': ('text',),
        'text/css': ('text',),
        'text/html': ('html', 'xhtml'),
        'text/xml': ('xml', 'xhtml'),
        'application/xml': ('xml', 'xhtml'),
        'application/xhtml+xml': ('xhtml',),
        'application/atom+xml': ('xml',),
        'application/rss+xml': ('xml',),
        'application/soap+xml': ('xml',),
        'image/svg+xml': ('xml',)}

    def __init__(self, loader):
        if not self.genshi_functions:
            from genshi import HTML, XML
            self.genshi_functions.update(HTML=HTML, XML=XML)
        self.load_template = loader.load

    @staticmethod
    def method_for_doctype(doctype):
        method = 'xhtml'
        if doctype:
            if doctype.startswith('html'):
                method = 'html'
            elif doctype.startswith('xhtml'):
                method = 'xhtml'
            elif doctype.startswith('svg'):
                method = 'xml'
            else:
                method = 'xhtml'
        return method

    def __call__(self, template_name, template_vars, **kwargs):
        """Render the template_vars with the Genshi template."""
        template_vars.update(self.genshi_functions)

        # Gets document type from content type or from config options
        doctype = kwargs.get('doctype')
        if not doctype:
            doctype = config.get('templating.genshi.doctype')
            if not doctype:
                method = kwargs.get('method') or config.get(
                    'templating.genshi.method') or 'xhtml'
                doctype = self.doctypes_for_methods.get(method)
            doctypes = self.doctypes_for_content_type.get(response.content_type)
            if doctypes and (not doctype or doctype not in doctypes):
                doctype = doctypes[0]
            kwargs['doctype'] = doctype

        # Gets rendering method from content type or from config options
        method = kwargs.get('method')
        if not method:
            method = config.get('templating.genshi.method')
            if not method:
                method = self.method_for_doctype(doctype)
            methods = self.methods_for_content_type.get(response.content_type)
            if methods and (not method or method not in methods):
                method = methods[0]
            kwargs['method'] = method

        def render_template():
            template_vars.update(my_pylons_globals())
            template = self.load_template(template_name)
            return literal(template.generate(**template_vars).render(
                    doctype=doctype, method=method, encoding=None))

        return templating.cached_template(
            template_name, render_template,
            ns_options=('doctype', 'method'), **kwargs)


def render_mako(template_name, template_vars, **kwargs):
    if asbool(config.get('use_dotted_templatenames', 'true')):
        template_name = tg.config['pylons.app_globals'].\
            dotted_filename_finder.get_dotted_filename(template_name, template_extension='.mak')

    return templating.render_mako(template_name, extra_vars=template_vars, **kwargs)


def render_jinja(template_name, template_vars, **kwargs):
    return templating.render_jinja2(template_name, extra_vars=template_vars,
                                   **kwargs)


def render_json(template_name, template_vars, **kwargs):
    return tg.json_encode(template_vars)


def render_kajiki(template_name, extra_vars=None, cache_key=None,
                  cache_type=None, cache_expire=None, method='xhtml'):
    """Render a template with Kajiki

    Accepts the cache options ``cache_key``, ``cache_type``, and
    ``cache_expire`` in addition to method which are passed to Kajiki's
    render function.

    """
    # Create a render callable for the cache function
    def render_template():
        # Pull in extra vars if needed
        globs = extra_vars or {}

        # Second, get the globals
        globs.update(templating.pylons_globals())

        # Grab a template reference
        template = globs['app_globals'].kajiki_loader.load(template_name)

        return literal(template(globs).render())

    return templating.cached_template(template_name, render_template, cache_key=cache_key,
                           cache_type=cache_type, cache_expire=cache_expire,
                           ns_options=('method'), method=method)

