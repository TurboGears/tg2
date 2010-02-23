from urllib import quote_plus

from pylons.configuration import config
from paste.deploy.converters import asbool
from pylons import (app_globals, session, tmpl_context, request,
                    response, templating)
from repoze.what import predicates

import tg
from tg.configuration import Bunch


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

    # TODO in 2.2: we should actually just get helpers from the package's helpers
    # module and dump the use of the SOP.
    
    #########
    #try: 
    #    helpers = config['package'].lib.helpers 
    #except ImportError: 
    #    helpers = Bunch()
    #########

    helpers = config.get('pylons.h') or config.get('pylons.helpers')

    
    root_vars = Bunch(
        c = tmpl_context,
        tmpl_context = tmpl_context,
        response = response,
        request = request,
        url = tg.url,
        helpers = helpers,
        tg = tg_vars
        )
    #Allow users to provide a callable that defines extra vars to be
    #added to the template namespace
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
        #Get the extra vars, and merge in the vars from the controller
        tg_vars = _get_tg_vars()
        tg_vars.update(template_vars)
        template_vars = tg_vars

    if not render_function:
        # getting the default renderer. (this is only if no engine was defined
        # in the @expose()
        render_function = config['render_functions'][config['default_renderer']]

    return render_function(template_name, template_vars, **kwargs)

def render_chameleon_genshi(template_name, template_vars, **kwargs):
    """Render the template_vars with the chameleon.genshi template"""
    # here we use the render genshi function because it should be api compliant
    return render_genshi(template_name, template_vars, **kwargs)


# demand load these items from Genshi if needed
HTML = XML = None
def render_genshi(template_name, template_vars, **kwargs):
    """Render the template_vars with the Genshi template"""
    global HTML,XML
    if not HTML or not XML:
        from genshi import HTML,XML

    template_vars.update(HTML=HTML, XML=XML)

    if config.get('use_dotted_templatenames', False):
        template_name = tg.config['pylons.app_globals'
                ].dotted_filename_finder.get_dotted_filename(
                        template_name,
                        template_extension='.html')

    if 'method' not in kwargs and 'templating.genshi.method' in config:
        kwargs['method'] = config['templating.genshi.method']
    # (in a similar way, we could pass other serialization options when they
    # will be supported - see http://pylonshq.com/project/pylonshq/ticket/613)

    return templating.render_genshi(template_name, extra_vars=template_vars,
                                    **kwargs)


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
