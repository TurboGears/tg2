from pylons import (app_globals, config, session, tmpl_context, request, 
                    response, templating)
import tg
from tg.util import get_dotted_filename
from tg.configuration import Bunch
from genshi import XML
from urllib import quote_plus

class MissingRendererError(Exception):
    def __init__(self, template_engine):
        super(MissingRendererError, self).__init__(
            ("The renderer for '%(template_engine)s' templates is missing. "
            "Try adding the following line in you app_cfg.py:\n"
            "\"base_config.renderers.append('%(template_engine)s')\"") % dict(
            template_engine=template_engine))
        self.template_engine = template_engine

def get_tg_vars():
    """Create a Bunch of variables that should be available in all templates.

    These variables are:

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
    """
    # TODO: Implement user_agent and other missing features. 
    tg_vars = Bunch(
        config = tg.config,
        flash = tg.get_flash(),
        flash_status = tg.get_status(),
        quote_plus = quote_plus, 
        url = tg.controllers.url, 
        session = session, 
        locale = tg.request.accept_language.best_matches(),
        errors = getattr(tmpl_context, "form_errors", {}),
        inputs = getattr(tmpl_context, "form_values", {}),
        request = tg.request,
        auth_stack_enabled = 'repoze.who.plugins' in tg.request.environ
        )
    
    # TODO: we should actually just get helpers from the package's helpers
    # module and dump the use of the SOP. 
    helpers = config.get('pylons.h') or config.get('pylons.helpers')
        
    root_vars = Bunch(
        c = tmpl_context,
        tmpl_context = tmpl_context,
        response = response,
        request = request,
        h = helpers,
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
    
    if template_engine is not None:
        # the engine was defined in the @expose()
        render_function = config['render_functions'].get(template_engine)

        if render_function is None:
            # engine was forced in @expose() but is not present in the
            # engine list, warn developper
            raise MissingRendererError(template_engine)
    
    if not template_vars: 
        template_vars={}

    template_vars.update(get_tg_vars())

    if not render_function:
        # getting the default renderer. (this is only if no engine was defined
        # in the @expose()
        render_function = config['render_functions'][config['default_renderer']]

    return render_function(template_name, template_vars, **kwargs)


def render_genshi(template_name, template_vars, **kwargs):
    """Render a the template_vars with the Genshi template"""
    template_vars['XML'] = XML

    if config.get('use_dotted_templatenames', False):
        template_name = get_dotted_filename(template_name,
                template_extension='.html')

    return templating.render_genshi(template_name, extra_vars=template_vars, 
                                    **kwargs)

def render_mako(template_name, template_vars, **kwargs):
    template_vars.update(get_tg_vars())

    if config.get('use_dotted_templatenames', False):
        template_name = get_dotted_filename(template_name,
                template_extension='.mak')

    return templating.render_mako(template_name, extra_vars=template_vars,
                                  **kwargs)
    
def render_jinja(template_name, template_vars, **kwargs):
    template_vars.update(get_tg_vars())
    return templating.render_jinja(template_name, extra_vars=template_vars,
                                   **kwargs)
