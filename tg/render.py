try:
    from urllib import quote_plus
except ImportError: #pragma: no cover
    from urllib.parse import quote_plus

from tg.support.converters import asbool
from markupsafe import Markup

import tg
from tg import predicates
from tg.util import Bunch


class MissingRendererError(Exception):
    def __init__(self, template_engine):
        Exception.__init__(self,
            ("The renderer for '%(template_engine)s' templates is missing. "
            "Try adding the following line in you app_cfg.py:\n"
            "\"base_config.renderers.append('%(template_engine)s')\"") % dict(
            template_engine=template_engine))
        self.template_engine = template_engine


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
        The :mod:`tg.predicates` module.

    """

    tgl = tg.request_local.context._current_obj()
    req = tgl.request
    conf = tgl.config
    tmpl_context = tgl.tmpl_context
    app_globals = tgl.app_globals
    translator = tgl.translator
    response = tgl.response
    session = tgl.session

    try:
        h = conf['package'].lib.helpers
    except (AttributeError, ImportError):
        h = Bunch()

    try:
        validation = req.validation
    except AttributeError:
        validation = {}

    # TODO: Implement user_agent and other missing features.
    tg_vars = Bunch(
        config=tg.config,
        flash_obj=tg.flash,
        quote_plus=quote_plus,
        url=tg.url,
        # this will be None if no identity
        identity = req.environ.get('repoze.who.identity'),
        session = session,
        locale = req.plain_languages,
        errors = validation and validation.errors,
        inputs = validation and validation.values,
        request = req,
        auth_stack_enabled = 'repoze.who.plugins' in req.environ,
        predicates = predicates)

    root_vars = Bunch(
        c=tmpl_context,
        tmpl_context=tmpl_context,
        response=response,
        request=req,
        config=conf,
        app_globals=app_globals,
        g=app_globals,
        session=session,
        url=tg.url,
        helpers=h,
        h=h,
        tg=tg_vars,
        translator=translator,
        ungettext=tg.i18n.ungettext,
        _=tg.i18n.ugettext,
        N_=tg.i18n.gettext_noop)

    # Allow users to provide a callable that defines extra vars to be
    # added to the template namespace
    variable_provider = conf.get('variable_provider', None)
    if variable_provider:
        root_vars.update(variable_provider())
    return root_vars

#Monkey patch pylons_globals for cases when pylons.templating is used
#instead of tg.render to programmatically render templates.
try: #pragma: no cover
    import pylons
    import pylons.templating
    pylons.templating.pylons_globals = _get_tg_vars
except ImportError:
    pass
# end monkeying around


def render(template_vars, template_engine=None, template_name=None, **kwargs):
    """Renders a specific template in current TurboGears context.

    Permits to manually render any template like TurboGears would for
    expositions. It also guarantees that the ``before_render_call`` and
    ``after_render_call`` hooks are called in the process.

    :param dict template_vars: This is the dictonary of variables that should
                               become available to the template. Template
                               vars can also include the ``tg_cache`` dictionary
                               which enables template caching.
    :param str template_engine: This is the template engine name, same as
                                specified inside AppConfig.renderers.
    :param str template_name: This is the template to render, can be specified
                              both as a path or using dotted notation if available.

    TurboGears injects some additional variables in the template context,
    those include:

        - tg.config -> like tg.config in controllers
        - tg.flash_obj -> the flash object, call ``render`` on it to display it.
        - tg.quote_plus -> function to perform percentage escaping (%xx)
        - tg.url -> like tg.url in controllers
        - tg.identity -> like tg.request.identity in controllers
        - tg.session -> like tg.session in controllers
        - tg.locale -> Languages of the current request
        - tg.errors -> Validation errors
        - tg.inputs -> Values submitted for validation
        - tg.request -> like tg.request in controllers
        - tg.auth_stack_enabled -> if authentication is enabled or not
        - tg.predicates -> like tg.predicates in controllers

        - tmpl_context -> like tg.tmpl_context in controllers
        - response -> like tg.response in controllers
        - request -> like tg.request in controllers
        - config -> like tg.config in controllers
        - app_globals -> like tg.app_globals in controllers
        - session -> like tg.session in controllers
        - url -> like tg.url in controllers
        - h -> Your application helpers
        - translator -> The current gettext translator
        - _ -> like tg.i18n.ugettext

    Additional variables can be added to every template by a
    ``variable_provider`` function inside the application
    configuration. This function is expected to return
    a ``dict`` with any variable that should be added
    the default template variables. It can even replace
    existing variables.

    """
    config = tg.config._current_obj()

    render_function = None
    if template_engine is not None:
        # the engine was defined in the @expose()
        render_function = config['render_functions'].get(template_engine)

        if render_function is None:
            # engine was forced in @expose() but is not present in the
            # engine list, warn developer
            raise MissingRendererError(template_engine)

    if not render_function:
        # getting the default renderer, if no engine was defined in @expose()
        template_engine = config['default_renderer']
        render_function = config['render_functions'][template_engine]

    if not template_vars:
        template_vars = {}

    caching_options = template_vars.get('tg_cache', {})
    kwargs['cache_key'] = caching_options.get('key')
    kwargs['cache_expire'] = caching_options.get('expire')
    kwargs['cache_type'] = caching_options.get('type')

    tg.hooks.notify('before_render_call', (template_engine, template_name, template_vars, kwargs))

    tg_vars = template_vars

    engines_without_vars = config['rendering_engines_without_vars']
    if template_engine not in engines_without_vars:
        # Get the extra vars, and merge in the vars from the controller
        tg_vars = _get_tg_vars()
        tg_vars.update(template_vars)

    kwargs['result'] = render_function(template_name, tg_vars, **kwargs)

    tg.hooks.notify('after_render_call', (template_engine, template_name, template_vars, kwargs))
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
    if cache_key is not None or cache_type is not None or cache_expire is not None:
        get_cache_kw = {}
        if cache_type is not None:
            get_cache_kw['type'] = cache_type

        if not cache_key:
            cache_key = 'default'
        if cache_expire == 'never':
            cache_expire = None

        namespace = template_name
        for name in ns_options:
            namespace += str(kwargs.get(name))

        cache = tg.cache.get_cache(namespace, **get_cache_kw)
        content = cache.get_value(cache_key, createfunc=render_func,
            expiretime=cache_expire)
        return content
    else:
        return render_func()

