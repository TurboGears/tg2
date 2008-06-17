from pylons import tmpl_context, config, app_globals
from pylons.templating import pylons_globals

def get_tg_vars():
    """Create and return a dictionary of global tg variables
    
    Render functions should call this to retrieve a list of global
    Pylons variables that should be included in the global template
    namespace if possible.
    
    Pylons variables that are returned in the dictionary:
        c, g, h, _, N_, config, request, response, translator,
        ungettext
    
    If SessionMiddleware is being used, ``session`` will also be
    available in the template namespace.
    
    """
    
    conf = pylons.config._current_obj()
    c = pylons.tmpl_context._current_obj()
    g=conf.get('pylons.app_globals') or conf['pylons.g']
    pylons_vars = dict(
        c=c,
        tmpl_context=c,
        config=conf,
        app_globals=g,
        g=g,
        h=conf.get('pylons.h') or pylons.h._current_obj(),
        request=pylons.request._current_obj(),
        response=pylons.response._current_obj(),
        translator=pylons.translator._current_obj(),
        ungettext=pylons.i18n.ungettext,
        _=pylons.i18n._,
        N_=pylons.i18n.N_
    )
    
    # If the session was overriden to be None, don't populate the session
    # var
    if pylons.config['pylons.environ_config'].get('session', True):
        pylons_vars['session'] = pylons.session._current_obj()
    log.debug("Created render namespace with pylons vars: %s", pylons_vars)
    return pylons_vars

def render(template_engine=None, template_name=None, template_vars):
    render_function = app_globals.renderers.get(template_engine, None)
    if not render_function:
        render_function = config['tg.default_renderer']
        render_function(template_name, template_vars)

def render_genshi(template_name, tmplate_vars):
    # Update the passed in vars with the globals
    tmpl_vars.update(pylons_globals())
    # Grab a template reference
    template = app_globals.genshi_loader.load(template_name)
    # Render the template
    return template.render(**tmpl_vars)
