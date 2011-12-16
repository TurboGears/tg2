import os, sys, logging, paste
from webob.exc import HTTPFound, HTTPNotFound

log = logging.getLogger(__name__)

import warnings
if sys.version_info[:2] == (2,4):
    warnings.warn('Python 2.4 support is deprecated, and will be removed in TurboGears 2.2', DeprecationWarning)

import tg
from tg import request_local
from tg.i18n import _get_translator
from tg.request_local import Request, Response

class RequestLocals(object):
    pass

class ContextObj(object):
    def __repr__(self):
        attrs = sorted((name, value)
                       for name, value in self.__dict__.iteritems()
                       if not name.startswith('_'))
        parts = []
        for name, value in attrs:
            value_repr = repr(value)
            if len(value_repr) > 70:
                value_repr = value_repr[:60] + '...' + value_repr[-5:]
            parts.append(' %s=%s' % (name, value_repr))
        return '<%s.%s at %s%s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)),
            ','.join(parts))

class AttribSafeContextObj(ContextObj):
    """The :term:`tmpl_context` object, with lax attribute access (
    returns '' when the attribute does not exist)"""
    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            return ''

class TGApp(object):
    def __init__(self, config=None, **kwargs):
        """Initialize a base WSGI application

        The base WSGI application requires several keywords, the
        package name, and the globals object. If no helpers object is
        provided then h will be None.

        """
        self.config = config = config or tg.config._current_obj()
        self.globals = config.get('tg.app_globals')
        self.package_name = config['package'].__name__

        self.controller_classes = {}
        self.config.setdefault('lang', None)

        # Cache some options for use during requests
        self.strict_tmpl_context = self.config['tg.strict_tmpl_context']
        self.pylons_compatible = self.config.get('tg.pylons_compatible', True)

        self.req_options = config.get('tg.request_options',
                                      dict(charset='utf-8',
                                           errors='replace',
                                           decode_param_names=False,
                                           language='en-us'))

        self.resp_options = config.get('tg.response_options',
                                       dict(content_type='text/html',
                                            charset='utf-8', errors='strict',
                                            headers={'Cache-Control': 'no-cache',
                                                     'Pragma': 'no-cache',
                                                     'Content-Type': None}))

    def setup_pylons_compatibility(self, environ, controller):
        """Updates environ to be backward compatible with Pylons"""
        try:
            import pylons

            environ['pylons.controller'] = controller
            environ['pylons.pylons'] = environ['tg.locals']
            environ['pylons.routes_dict'] = environ['tg.routes_dict']

            self.config['pylons.app_globals'] = self.globals

            pylons.request = request_local.request
            pylons.cache = request_local.request
            pylons.config = request_local.config
            pylons.app_globals = request_local.app_globals
            pylons.session = request_local.session
            pylons.translator = request_local.translator
            pylons.url = request_local.url
            pylons.response = request_local.response
            pylons.tmpl_context = request_local.tmpl_context
        except ImportError:
            pass

    def __call__(self, environ, start_response):
        testmode = self.setup_app_env(environ, start_response)
        if testmode:
            if environ['PATH_INFO'] == '/_test_vars':
                paste.registry.restorer.save_registry_state(environ)
                start_response('200 OK', [('Content-type', 'text/plain')])
                return ['%s' % paste.registry.restorer.get_request_id(environ)]

        controller = self.resolve(environ, start_response)
        response = self.dispatch(controller, environ, start_response)

        if testmode and hasattr(response, 'wsgi_response'):
            environ['paste.testing_variables']['response'] = response

        try:
            if response is not None:
                return response

            raise Exception("No content returned by controller (Did you "
                            "remember to 'return' it?) in: %r" %
                            controller.__name__)
        finally:
            # Help Python collect ram a bit faster by removing the reference
            # cycle that the thread local objects cause
            if 'tg.locals' in environ:
                del environ['tg.locals']

    def setup_app_env(self, environ, start_response):
        """Setup and register all the Pylons objects with the registry

        After creating all the global objects for use in the request,
        :meth:`~PylonsApp.register_globals` is called to register them
        in the environment.

        """

        # Setup the basic global objects
        req_options = self.req_options
        req = Request(environ, charset=req_options['charset'],
                      unicode_errors=req_options['errors'],
                      decode_param_names=req_options['decode_param_names'])
        req.language = req_options['language']

        resp_options = self.resp_options
        response = Response(
            content_type=resp_options['content_type'],
            charset=resp_options['charset'])
        response.headers.update(resp_options['headers'])

        # Setup the translator object
        lang = self.config['lang']
        translator = _get_translator(lang, tg_config=self.config)

        if self.strict_tmpl_context:
            tmpl_context = ContextObj()
        else:
            tmpl_context = AttribSafeContextObj()

        locals = RequestLocals()
        locals.response = response
        locals.request = req
        locals.app_globals = self.globals
        locals.config = self.config
        locals.tmpl_context = tmpl_context
        locals.translator = translator
        locals.session = environ['beaker.session']
        locals.cache = environ['beaker.cache']
        locals.url = environ['routes.url']

        environ['tg.locals'] = locals

        #Register Global objects
        registry = environ['paste.registry']
        registry.register(request_local.response, response)
        registry.register(request_local.request, req)
        registry.register(request_local.app_globals, self.globals)
        registry.register(request_local.config, self.config)
        registry.register(request_local.tmpl_context, tmpl_context)
        registry.register(request_local.translator, translator)
        registry.register(request_local.session, locals.session)
        registry.register(request_local.cache, locals.cache)
        registry.register(request_local.url, locals.url)

        if 'paste.testing_variables' in environ:
            testenv = environ['paste.testing_variables']
            testenv['req'] = req
            testenv['response'] = response
            testenv['tmpl_context'] = tmpl_context
            testenv['app_globals'] = testenv['g'] = self.globals
            testenv['config'] = self.config
            testenv['session'] = locals.session
            testenv['cache'] = locals.cache
            return True

        return False

    def resolve(self, environ, start_response):
        """Uses dispatching information found in
        ``environ['wsgiorg.routing_args']`` to retrieve a controller
        name and return the controller instance from the appropriate
        controller module.

        Override this to change how the controller name is found and
        returned.

        """
        match = environ['wsgiorg.routing_args'][1]
        environ['tg.routes_dict'] = match
        controller = match.get('controller')
        if not controller:
            return None

        return self.find_controller(controller)

    def class_name_from_module_name(self, module_name):
        words = module_name.replace('-', '_').split('_')
        return ''.join(w.title() for w in words)

    def find_controller(self, controller):
        """Locates a controller by attempting to import it then grab
        the SomeController instance from the imported module.

        Override this to change how the controller object is found once
        the URL has been resolved.

        """
        # Check to see if we've cached the class instance for this name
        if controller in self.controller_classes:
            return self.controller_classes[controller]

        root_module_path = self.config['paths']['root']
        base_controller_path = self.config['paths']['controllers']

        #remove the part of the path we expect to be the root part (plus one '/')
        assert base_controller_path.startswith(root_module_path)
        controller_path = base_controller_path[len(root_module_path)+1:]

        #attach the package
        full_module_name = '.'.join([self.package_name] +
            controller_path.split(os.sep) + controller.split('/'))

        # Hide the traceback here if the import fails (bad syntax and such)
        __traceback_hide__ = 'before_and_this'

        __import__(full_module_name)
        module_name = controller.split('/')[-1]
        class_name = self.class_name_from_module_name(module_name) + 'Controller'
        mycontroller = getattr(sys.modules[full_module_name], class_name)
        self.controller_classes[controller] = mycontroller
        return mycontroller

    def dispatch(self, controller, environ, start_response):
        """Dispatches to a controller, will instantiate the controller
        if necessary.

        Override this to change how the controller dispatch is handled.

        """
        if not controller:
            return HTTPNotFound()(environ, start_response)

        # If it's a class, instantiate it
        if hasattr(controller, '__bases__'):
            controller = controller()

        #Setup pylons compatibility before calling controller
        if self.pylons_compatible:
            self.setup_pylons_compatibility(environ, controller)

        # Controller is assumed to handle a WSGI call
        return controller(environ, start_response)
