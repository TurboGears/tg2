from pylons import (app_globals, config, session, tmpl_context, request, 
                    response, templating)
import tg
from tg.configuration import Bunch
from genshi import XML
from urllib import quote_plus
from itertools import cycle as icycle, chain

class MissingRendererError(Exception):
    def __init__(self, template_engine):
        super(MissingRendererError, self).__init__(
            ("The renderer for '%(template_engine)s' templates is missing. "
            "Try adding the following line in you app_cfg.py:\n"
            "\"base_config.renderers.append('%(template_engine)s')\"") % dict(
            template_engine=template_engine))
        self.template_engine = template_engine

class cycle:
    """
    Loops forever over an iterator. Wraps the itertools.cycle method
    but provides a way to get the current value via the 'value' attribute

    >>> from tg.render import cycle
    >>> oe = cycle(('odd','even'))
    >>> oe
    None
    >>> oe.next()
    'odd'
    >>> oe
    'odd'
    >>> oe.next()
    'even'
    >>> oe.next()
    'odd'
    >>> oe.value
    'odd'
    """
    value = None
    def __init__(self, iterable):
        self._cycle = icycle(iterable)
    def __str__(self):
        return self.value.__str__()
    def __repr__(self):
        return self.value.__repr__()
    def next(self):
        self.value = self._cycle.next()
        return self.value

def selector(expression):
    """If the expression is true, return the string 'selected'. Useful for
    HTML <option>s."""
    if expression:
        return "selected"
    else:
        return None

def checker(expression):
    """If the expression is true, return the string "checked". This is useful
    for checkbox inputs.
    """
    if expression:
        return "checked"
    else:
        return None

def ipeek(it):
    """Lets you look at the first item in an iterator. This is a good way
    to verify that the iterator actually contains something. This is useful
    for cases where you will choose not to display a list or table if there
    is no data present.
    """
    it = iter(it)
    try:
        item = it.next()
        return chain([item], it)
    except StopIteration:
        return None

def get_tg_vars():
    """Create a Bunch of variables that should be available in all templates.

    These variables are:

    selector
        the selector function
    checker
        the checker function
    tg_js
        the path to the JavaScript libraries
    ipeek
        the ipeek function
    cycle
        cycle through a set of values
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
        selector=selector,
        ipeek=ipeek, 
        cycle=cycle, 
        flash=tg.get_flash(),
        flash_status=tg.get_status(),
        quote_plus=quote_plus, 
        checker=checker,
        url = tg.controllers.url, 
        session=session, 
        config=config,
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
        c=tmpl_context,
        tmpl_context = tmpl_context,
        response = response,
        request = request,
        h = helpers,
        url = tg.url,
        helpers = helpers,
        tg=tg_vars
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
            # engine was force in @expose() but is not present in the
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

def get_dotted_filename(template_name, template_extension='.html'):
    """this helper function is designed to search a template or any other
    file by python module name.

    Given a string containing the file/template name passed to the @expose
    decorator we will return a resource useable as a filename even
    if the file is in fact inside a zipped egg.

    The actual implementation is a revamp of the Genshi buffet support
    plugin, but could be used with any kind a file inside a python package.

    @param template_name: the string representation of the template name
    as it has been given by the user on his @expose decorator.
    Basically this will be a string in the form of:
    "genshi:myapp.templates.somename"
    @type template_name: string

    @param template_extension: the extension we excpect the template to have,
    this MUST be the full extension as returned by the os.path.splitext
    function. This means it should contain the dot. ie: '.html'

    This argument is optional and the default value if nothing is provided will
    be '.html'
    @type template_extension: string
    """
    divider = template_name.rfind('.')
    if divider >= 0:
        from pkg_resources import resource_filename
        package = template_name[:divider]
        basename = template_name[divider + 1:] + template_extension
        result = resource_filename(package, basename)

    else:
        result = template_name

    return result

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
