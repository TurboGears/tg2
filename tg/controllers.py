"""Classes and methods for TurboGears controllers."""
from pylons.controllers import WSGIController
import pylons
from util import to_kw, from_kw
#from turbojson.jsonify import jsonify

import urlparse
import formencode
from formencode.variabledecode import variable_decode

from dispatch import object_dispatch


def _configured_engines():
    """Returns set with the currently configured template engine's names from
    the active application's globals"""
    g = pylons.g._current_obj()
    if not hasattr(g, 'tg_configured_engines'):
        g.tg_configured_engines = set()
    return g.tg_configured_engines





def error_for(name):
    '''Returns the error value for a particular filed name.'''
    #TODO: Move tg_errors into the tg_info object?
    err = pylons.c.tg_errors.get(name)
    if err is None:
        return None
    return err

def value_for(name):
    '''Returns the value for a particular form field when the form is redisplayed
    to show error messages'''
    #TODO: Move the tg_values object into tg_info?
    return pylons.c.tg_values.get(name)

class TurboGearsController(WSGIController):
    
    def _tg_initialize_app_context(self):
        """Place tg specific attributes at app's context."""
        pylons.c.tg_errors = {}
        pylons.c.tg_values = {}
        #XXX These funcs. better at h?
        pylons.c.error_for=error_for
        pylons.c.value_for=value_for

    def _tg_routing_info(self, url):
        """
        Returns a tuple (controller, remainder, params) 
        
        :Parameters:
          url
            url as string
        """
        url_path = url.split('/')
        controller, remainder = object_dispatch(self, url_path)
        #XXX Place controller url at context temporarily... we should be
        #    really using SCRIPT_NAME for this.
        if remainder:
            pylons.c.controller_url = '/'.join(url_path[:-len(remainder)])
        else:
            pylons.c.controller_url = url
        if remainder and remainder[-1] == '': remainder.pop()
        return controller, remainder, pylons.request.params

    def _tg_validate(self, controller, params):
        params = variable_decode(params)
        if controller.tg_info.validator:
            params = controller.tg_info.validator.to_python(params)
        return params

    def _tg_render_response(self, controller, response):
        '''Render response takes the dictionary returned by the controller calls        the apropriate template engine. It uses information off of the tg_info 
        object to decide which engine and template to use, and removes anything 
        in the exclude_names list.  All of these values are populated into the
        context object by the expose decorator. 
        '''
        content_type, engine_name, template_name, exclude_names = \
                      controller.tg_info.lookup_template_engine(pylons.request)
        if template_name is None: return response
        if engine_name not in _configured_engines():
            pylons.buffet.prepare(engine_name)
            _configured_engines().add(engine_name)
        namespace = dict(context=pylons.c)
        namespace.update(response)
        for name in exclude_names:
            namespace.pop(name)
        result = pylons.buffet.render(engine_name=engine_name,
                                      template_name=template_name,
                                      include_pylons_variables=False,
                                      namespace=namespace)
        response = pylons.Response(result)
        response.headers['Content-Type'] = content_type
        return response

    def _tg_handle_validation_errors(self, controller, exception):
        """Handles the Invalid exception raised when trying to call the
        controller method.
        
        Returns an error_handler method (could be the same controller method)
        and whatever that method returned"""
        pylons.c.tg_errors = exception.error_dict
        pylons.c.tg_values = exception.value
        error_handler = controller.tg_info.error_handler
        if not error_handler: raise
        if isinstance(error_handler, basestring):
            controller_url = pylons.c.controller_url
            error_handler_absolute_url = urlparse.urljoin(controller_url, error_handler)
            error_handler, remainder = object_dispatch(self, error_handler_absolute_url.split('/'))
            if remainder and remainder[-1] == '': remainder.pop()
            output = error_handler(*remainder)
        else:
            output = error_handler(controller.im_self)
        return error_handler, output

    def route(self, url='/', start_response=None, **kw):
        self._tg_initialize_app_context()
        try:
            # Lookup controller
            controller, remainder, params = self._tg_routing_info(url)

            # Convert positional args to keyword args
            remainder, params = to_kw(controller, remainder, params)
            kw_self = params.pop('self', None)
            pylons.request.headers['tg_format'] = params.pop('tg_format', None)

            # Validate user input
            controller.tg_info.run_hooks('before_validate', remainder, params)
            params = self._tg_validate(controller, params)
            pylons.c.tg_values = params

            # call controller
            if kw_self:
                params['self'] = kw_self
            remainder, params = from_kw(controller, remainder, params)
            controller.tg_info.run_hooks('before_call', remainder, params)
            output = controller(*remainder, **params)

        except formencode.api.Invalid, inv:
            controller, output = self._tg_handle_validation_errors(controller, inv)

        # Render template
        controller.tg_info.run_hooks('before_render', remainder, params, output)
        response = self._tg_render_response(controller, output)
        controller.tg_info.run_hooks('after_render', response)
        return response
            

