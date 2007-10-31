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
    err = pylons.c.tg_errors.get(name)
    if err is None:
        return None
    return err

def value_for(name):
    '''Returns the value for a particular form field when the form is redisplayed
    to show error messages'''
    return pylons.c.tg_values.get(name)

class TurboGearsController(WSGIController):
    
    def _tg_initialize_app_context(self):
        """Place tg specific attributes at app's context."""
        pylons.c.tg_errors = {}
        pylons.c.tg_values = {}
        
        
        #TODO: Pylons.h is gone away... we need someplace better to put these functions. 
        #I'm throwing them on the context object, but it is an ugly hack! --Mark
        #since these are just functions, perhaps we can keep them in the tg namespace directly...
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
        '''Render response takes the dictionary returned by the controller calls
        the apropriate template engine. It uses information off of the tg_info 
        object to decide which engine and template to use, and removes anything 
        in the exclude_names list from the returned dictionary. 

        The exclude_names funtionality  allows you to pass variables to some 
        template rendering engines, but not others. This behavior is particularly 
        usefull for rendering engines like JSON or other "web service" style 
        engines which don't use and explicit template.

        All of these values are populated into the context object by the 
        expose decorator. 
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
        pylons.response.headers['Content-Type'] = content_type
        return result

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
        '''The route method is the default action called for all URL's in the
        application, at least when you use the default route as set up in the 
        standard turbogears quickstart. 

        Route looks through the controller class to find matching methods, walking
        down the object hierarchy untill a match is found.  A classes Index matches / 
        and the default method is called if no matching method is called.  
        
        We have not yet implemented cherrypy's mechanisim that replaces dots in the URL
        with underscores when looking up a method name.
        
        To implement custom dispatch, all you have to do is overide this method. 
        
        But TurboGears2 also implements a Quxote inspired ookup method which allows 
        you to do customized dispatch at any time. 
        
        Lookup and default are called in identical situations: when "normal"
        object traversal is not able to find an exposed method, it begins
        popping the stack of "not found" handlers.  If the handler is a
        "default" method, it is called with the rest of the path as positional
        parameters passed into the default method.   
        
        The not found handler stack can also contain "lookup" methods, which
        are different, as they are not actual controllers. 
        
        A lookup method takes as its argument the remaining path elements and
        returns an object (representing the next step in the traversal) and a
        (possibly modified) list of remaining path elements.  So a blog might
        have controllers that look something like this:

        class BlogController(Controller):
           @expose()
           def lookup(self, year, month, day, id, *remainder):
              dt = date(int(year), int(month), int(day))
              return BlogEntryController(dt, int(id)), remainder

        class BlogEntryController(Controller):
           def __init__(self, dt, id):
               self.entry = model.BlogEntry.get_by(date=dt, id=id)
           @expose(...)
           def index(self):
              ...
           @expose(...)
           def edit(self):
              ...
           @expose()
           def update(self):
              ....

        So a URL request to .../2007/6/28/0/edit would map to
        BlogEntryController(date(2007,6,28), 0).edit .  In other situations, 
        you might have a several-layers-deep "lookup" chain, e.g. for 
        editing hierarchical data (/client/1/project/2/task/3/edit).  
        
        The benefit over "default" handlers is that you _return_ a controller 
        and continue traversing rather than _being_ a controller and 
        stopping traversal altogether.  Plus, it makes semi-RESTful URLs easy.
        '''
        
        #TODO: We need to think about cp's ./_ replacment how it interacts with content negotiation
        #TODO: Implement replacmement of dots with underscores in method name lookup. 
        
        self._tg_initialize_app_context()
        try:
            # Lookup controller method
            controller, remainder, params = self._tg_routing_info(url)

            # Convert positional args to keyword args
            remainder, params = to_kw(controller, remainder, params)
            kw_self = params.pop('self', None)
            pylons.request.headers['tg_format'] = params.pop('tg_format', None)

            # Validate user input
            controller.tg_info.run_hooks('before_validate', remainder, params)
            params = self._tg_validate(controller, params)
            pylons.c.tg_values = params

            # call controller method
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
            

