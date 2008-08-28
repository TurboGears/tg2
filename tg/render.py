from pylons import (app_globals, config, session, tmpl_context, request, 
                    response, templating)
from pylons import h as pylons_helpers
import tg
from tg.configuration import Bunch
from genshi import XML
from urllib import quote_plus

class cycle:
    """
    Loops forever over an iterator. Wraps the itertools.cycle method
    but provides a way to get the current value via the 'value' attribute

    >>> from turbogears.view.base import cycle
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
    """
    # TODO: Implement user_agent and other missing features. 
    tg_vars = Bunch(
        selector=selector,
        ipeek=ipeek, 
        cycle=cycle, 
        quote_plus=quote_plus, 
        checker=checker,
        url = tg.controllers.url, 
        session=session, 
        config=config,
        locale = tg.request.accept_language.best_matches(),
        errors = getattr(tmpl_context, "form_errors", {}),
        inputs = getattr(tmpl_context, "form_values", {}),
        request = tg.request
        )
        
    helpers = config.get('pylons.h') or pylons_helpers._current_obj()
    
    root_vars = Bunch(
        c=tmpl_context,
        tmpl_context = tmpl_context,
        response = response,
        request = request,
        h = helpers,
        helpers = helpers,
        tg=tg_vars
        )
    return root_vars
    
def genshi_template_loader():
    pass

def render(template_vars, template_engine=None, template_name=None, **kwargs):
    
    render_function = config['render_functions'].get(template_engine)
    
    if not template_vars: 
        template_vars={}
    template_vars.update(get_tg_vars())
    if not render_function:
        render_function = config['render_functions'][config['default_renderer']]
    return render_function(template_name, template_vars, **kwargs)

def render_genshi(template_name, template_vars, **kwargs):
    """Render a the template_vars with the Genshi template"""
    template_vars['XML'] = XML
    return templating.render_genshi(template_name, extra_vars=template_vars, 
                                    **kwargs)

def render_mako(template_name, template_vars, **kwargs):
    tmpl_vars.update(get_tg_vars())
    return templating.render_mako(template_name, extra_vars=template_vars,
                                  **kwargs)
    
def render_jinja(template_name, template_vars, **kwargs):
    tmpl_vars.update(get_tg_vars())
    return templating.render_jinja(template_name, extra_vars=template_vars,
                                   **kwargs)
