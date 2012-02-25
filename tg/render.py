from urllib import quote_plus

from paste.deploy.converters import asbool

try:
    from repoze.what import predicates
except ImportError:
    predicates = []

from webhelpers.html import literal

import tg
from tg.configuration import Bunch

from webhelpers.html import literal


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

    req = tg.request._current_obj()
    conf = tg.config._current_obj()
    tmpl_context = tg.tmpl_context._current_obj()
    app_globals = tg.app_globals._current_obj()
    translator = tg.translator._current_obj()
    response = tg.response._current_obj()

    try:
        h = conf['package'].lib.helpers
    except AttributeError, ImportError:
        h = Bunch()

    # TODO: Implement user_agent and other missing features.
    tg_vars = Bunch(
        config=tg.config,
        flash_obj=tg.flash,
        flash=DeprecatedFlashVariable(
            lambda: tg.flash.message,
            "flash is deprecated, please use flash_obj.message instead "
            "or use the new flash_obj.render() method"
            ),
        flash_status=DeprecatedFlashVariable(
            lambda: 'status_' + tg.flash.status,
            "flash_status is deprecated, please use flash_obj.status instead "
            "or use the new flash_obj.render() method"
            ),
        quote_plus=quote_plus,
        url=tg.url,
        # this will be None if no identity
        identity=req.environ.get('repoze.who.identity'),
        session=tg.session,
        locale=req.accept_language.best_matches(),
        errors=getattr(tmpl_context, "form_errors", {}),
        inputs=getattr(tmpl_context, "form_values", {}),
        request=req,
        auth_stack_enabled='repoze.who.plugins' in req.environ,
        predicates=predicates)

    root_vars = Bunch(
        c=tmpl_context,
        tmpl_context=tmpl_context,
        response=response,
        request=req,
        config=conf,
        app_globals=app_globals,
        g=app_globals,
        url=tg.url,
        helpers=h,
        h=h,
        tg=tg_vars,
        translator=translator,
        ungettext=tg.i18n.ungettext,
        _=tg.i18n.ugettext,
        N_=tg.i18n.gettext_noop)

    econf = conf['pylons.environ_config']
    if 'beaker.session' in req.environ or \
        ('session' in econf and econf['session'] in req.environ):
        root_vars['session'] = tg.session._current_obj()

    # Allow users to provide a callable that defines extra vars to be
    # added to the template namespace
    variable_provider = conf.get('variable_provider', None)
    if variable_provider:
        root_vars.update(variable_provider())
    return root_vars

# Monkey patch pylons_globals for cases when pylons.templating is used
# instead of tg.render to programmatically render templates.
import pylons
pylons.templating.pylons_globals = _get_tg_vars
# end monkeying around


def render(template_vars, template_engine=None, template_name=None, **kwargs):
    config = tg.config._current_obj()

    render_function = None
    if template_engine is not None:
        # the engine was defined in the @expose()
        render_function = config['render_functions'].get(template_engine)

        if render_function is None:
            # engine was forced in @expose() but is not present in the
            # engine list, warn developer
            raise MissingRendererError(template_engine)

    if not template_vars:
        template_vars = {}

    caching_options = template_vars.get('tg_cache', {})
    kwargs['cache_key'] = caching_options.get('key')
    kwargs['cache_expire'] = caching_options.get('expire')
    kwargs['cache_type'] = caching_options.get('type')

    for func in config.get('hooks', {}).get('before_render_call', []):
        func(template_engine, template_name, template_vars, kwargs)

    tg_vars = template_vars
    if template_engine not in ("json", 'amf'):
        # Get the extra vars, and merge in the vars from the controller
        tg_vars = _get_tg_vars()
        tg_vars.update(template_vars)

    if not render_function:
        # getting the default renderer, if no engine was defined in @expose()
        render_function = config[
            'render_functions'][config['default_renderer']]

    kwargs['result'] = render_function(template_name, tg_vars, **kwargs)

    for func in config.get('hooks', {}).get('after_render_call', []):
        func(template_engine, template_name, template_vars, kwargs)

    return kwargs['result']


def cached_template(template_name, render_func, ns_options=(),
                    cache_key=None, cache_type=None, cache_expire=None,
                    **kwargs):
    """Cache and render a template, took from Pylons

    Cache a template to the namespace ``template_name``, along with a
    specific key if provided.

    Basic Options

    ``template_name``
        Name of the template, which is used as the template namespace.
    ``render_func``
        Function used to generate the template should it no longer be
        valid or doesn't exist in the cache.
    ``ns_options``
        Tuple of strings, that should correspond to keys likely to be
        in the ``kwargs`` that should be used to construct the
        namespace used for the cache. For example, if the template
        language supports the 'fragment' option, the namespace should
        include it so that the cached copy for a template is not the
        same as the fragment version of it.

    Caching options (uses Beaker caching middleware)

    ``cache_key``
        Key to cache this copy of the template under.
    ``cache_type``
        Valid options are ``dbm``, ``file``, ``memory``, ``database``,
        or ``memcached``.
    ``cache_expire``
        Time in seconds to cache this template with this ``cache_key``
        for. Or use 'never' to designate that the cache should never
        expire.

    The minimum key required to trigger caching is
    ``cache_expire='never'`` which will cache the template forever
    seconds with no key.

    """
    # If one of them is not None then the user did set something
    if (cache_key is not None
            or cache_expire is not None or cache_type is not None):
        if not cache_type:
            cache_type = 'dbm'
        if not cache_key:
            cache_key = 'default'
        if cache_expire == 'never':
            cache_expire = None
        namespace = template_name
        for name in ns_options:
            namespace += str(kwargs.get(name))
        cache = tg.cache.get_cache(namespace, type=cache_type)
        content = cache.get_value(cache_key, createfunc=render_func,
            expiretime=cache_expire)
        return content
    else:
        return render_func()


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
        config = tg.config._current_obj()

        # Gets template format from content type or from config options
        format = kwargs.get('format')
        if not format:
            format = self.format_for_content_type.get(tg.response.content_type)
            if not format:
                format = config.get('templating.chameleon.genshi.format')
                if not format:
                    format = config.get('templating.genshi.method')
                    if not format or format not in ('xml', 'text'):
                        format = 'xml'

        def render_template():
            template = self.load_template(template_name, format=format)
            return literal(template.render(**template_vars))

        return cached_template(template_name, render_template,
                               ns_options=('doctype', 'method'), **kwargs)


class RenderGenshi(object):
    """Singleton that can be called as the Genshi render function."""

    genshi_functions = {}  # auxiliary Genshi functions loaded on demand

    default_doctype = default_method = None

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
        'image/svg+xml': ('svg', 'svg-full', 'svg-basic', 'svg-tiny')}

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
        doctype = tg.config.get('templating.genshi.doctype')
        if doctype:
            if isinstance(doctype, str):
                self.default_doctype = doctype
            elif isinstance(doctype, dict):
                doctypes = self.doctypes_for_content_type.copy()
                doctypes.update(doctype)
                self.doctypes_for_content_type = doctypes
        method = tg.config.get('templating.genshi.method')
        if method:
            if isinstance(method, str):
                self.default_method = method
            elif isinstance(method, dict):
                methods = self.methods_for_content_type.copy()
                methods.update(method)
                self.methods_for_content_type = methods

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
        """Render the template_vars with the Genshi template.

        If you don't pass a doctype or pass 'auto' as the doctype,
        then the doctype will be automatically determined.
        If you pass a doctype of None, then no doctype will be injected.
        If you don't pass a method or pass 'auto' as the method,
        then the method will be automatically determined.

        """
        response = tg.response._current_obj()

        template_vars.update(self.genshi_functions)

        # Gets document type from content type or from config options
        doctype = kwargs.get('doctype', 'auto')
        if doctype == 'auto':
            doctype = self.default_doctype
            if not doctype:
                method = kwargs.get('method') or self.default_method or 'xhtml'
                doctype = self.doctypes_for_methods.get(method)
            doctypes = self.doctypes_for_content_type.get(response.content_type)
            if doctypes and (not doctype or doctype not in doctypes):
                doctype = doctypes[0]
            kwargs['doctype'] = doctype

        # Gets rendering method from content type or from config options
        method = kwargs.get('method')
        if not method or method == 'auto':
            method = self.default_method
            if not method:
                method = self.method_for_doctype(doctype)
            methods = self.methods_for_content_type.get(response.content_type)
            if methods and (not method or method not in methods):
                method = methods[0]
            kwargs['method'] = method

        def render_template():
            template = self.load_template(template_name)
            return literal(template.generate(**template_vars).render(
                    doctype=doctype, method=method, encoding=None))

        return cached_template(template_name, render_template,
                               ns_options=('doctype', 'method'), **kwargs)


def render_mako(template_name, globs,
        cache_key=None, cache_type=None, cache_expire=None):
    config = tg.config._current_obj()

    if asbool(config.get('use_dotted_templatenames', 'true')):
        template_name = globs[
            'app_globals'].dotted_filename_finder.get_dotted_filename(
                template_name, template_extension='.mak')

    # Create a render callable for the cache function
    def render_template():
        # Grab a template reference
        template = globs['app_globals'].mako_lookup.get_template(template_name)
        return literal(template.render_unicode(**globs))

    return cached_template(template_name, render_template, cache_key=cache_key,
                           cache_type=cache_type, cache_expire=cache_expire)


def render_json(template_name, template_vars, **kwargs):
    return tg.json_encode(template_vars)


def render_kajiki(template_name, globs, cache_key=None,
                  cache_type=None, cache_expire=None, method='xhtml'):
    """Render a template with Kajiki

    Accepts the cache options ``cache_key``, ``cache_type``, and
    ``cache_expire`` in addition to method which are passed to Kajiki's
    render function.

    """
    # Create a render callable for the cache function
    def render_template():
        # Grab a template reference
        template = globs['app_globals'].kajiki_loader.load(template_name)
        return literal(template(globs).render())

    return cached_template(template_name, render_template,
        cache_key=cache_key, cache_type=cache_type, cache_expire=cache_expire,
        ns_options=('method'), method=method)


def render_jinja(template_name, globs, cache_key=None,
                 cache_type=None, cache_expire=None):
    """Render a template with Jinja2

    Accepts the cache options ``cache_key``, ``cache_type``, and
    ``cache_expire``.

    """
    # Create a render callable for the cache function
    def render_template():
        # Grab a template reference
        template = globs['app_globals'].jinja2_env.get_template(template_name)
        return literal(template.render(**globs))

    return cached_template(template_name, render_template,
        cache_key=cache_key, cache_type=cache_type, cache_expire=cache_expire)

