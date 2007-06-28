from pylons.controllers import WSGIController
import pylons
from util import to_kw
from turbojson.jsonify import jsonify

import urlparse
import formencode
from formencode.variabledecode import variable_decode

from dispatch import object_dispatch

_configured_engines = set()

#TODO:  We make render response return a string if passed a string??

def render_response(controller, response):
    ''' Render response takes the dictionary returned by the controller calls 
    the apropriate template engine.   It uses information off of the tg_info 
    object to decide which engine and template to use, and removes anything 
    in the exclude_names list.  All of these values are populated into the context 
    object by the expose decorator. 
    '''
    content_type, engine_name, template_name, exclude_names = \
                  controller.tg_info.lookup_template_engine(pylons.request)
    if template_name is None: return response
    if engine_name not in _configured_engines:
        pylons.buffet.prepare(engine_name)
        _configured_engines.add(engine_name)
    namespace = dict(context=pylons.c)
    namespace.update(response)
    for name in exclude_names:
        namespace.pop(name)
    result = pylons.buffet.render(engine_name=engine_name,
                                  template_name=template_name,
                                  include_pylons_variables=True,
                                  namespace=namespace)
    response = pylons.Response(result)
    response.headers['Content-Type'] = content_type
    return response



def error_for(name):
    '''Returns the error value for a particular filed name.'''
    #TODO: Move tg_errors into the tg_info object?
    err = pylons.c.tg_errors.get(name)
    if err is None: return None
    return err

def value_for(name):
    '''Returns the value for a particular form field when the form is redisplayed
    to show error messages'''
    #TODO: Move the tg_values object into tg_info?
    return pylons.c.tg_values.get(name)

class TurboGearsController(WSGIController):
    
    def route(self, url='/', start_response=None, **kw):
        pylons.c.tg_errors = {}
        pylons.c.tg_values = {}
        pylons.c.error_for=error_for
        pylons.c.value_for=value_for
        try:
            # Lookup controller
            url_path = url.split('/')
            controller, remainder = object_dispatch(self, url_path)
            if remainder:
                controller_url = '/'.join(url_path[:-len(remainder)])
            else:
                controller_url = url
            if remainder and remainder[-1] == '': remainder.pop()

            # Convert positional args to keyword args
            remainder, params = to_kw(controller, remainder, pylons.request.params)
            kw_self = params.pop('self', None)
            pylons.request.headers['tg_format'] = params.pop('tg_format', None)

            # Validate user input
            controller.tg_info.run_hooks('before_validate', remainder, params)
            params = variable_decode(params)
            if controller.tg_info.validator:
                params = controller.tg_info.validator.to_python(params)
            pylons.c.tg_values = params
            controller.tg_info.run_hooks('before_call', remainder, params)
            response = controller(*remainder, **params)
            controller.tg_info.run_hooks('before_render', remainder, params, response)
            # Render template
            response = render_response(controller, response)
            controller.tg_info.run_hooks('after_render', response)
            return response
        except formencode.api.Invalid, inv:
            pylons.c.tg_errors = inv.error_dict
            pylons.c.tg_values = params
            error_handler = controller.tg_info.error_handler
            if not error_handler: raise
            if isinstance(error_handler, basestring):
                error_handler_absolute_url = urlparse.urljoin(controller_url, error_handler)
                error_handler, remainder = object_dispatch(self, error_handler_absolute_url.split('/'))
                if remainder and remainder[-1] == '': remainder.pop()
                response = error_handler(*remainder)
            else:
                response = error_handler(controller.im_self)
            response = render_response(error_handler, response)
            return response
            

