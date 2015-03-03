import os, sys, logging
import warnings
from webob.exc import HTTPNotFound

log = logging.getLogger(__name__)

import tg
from tg import request_local
from tg.i18n import _get_translator
from tg.request_local import Request, Response

try: #pragma: no cover
    import pylons
    has_pylons = True
except:
    has_pylons = False


class RequestLocals(object):
    __slots__ = ('response', 'request', 'app_globals',
                 'config', 'tmpl_context', 'translator',
                 'session', 'cache', 'url')


class TGApp(object):
    def __init__(self, config=None, **kwargs):
        """Initialize a base WSGI application

        Given an application configuration creates the WSGI
        application for it, if no configuration is provided
        then tg.config is used.

        TGApp constructor is also in charge of actually
        initializing application wrappers.
        """
        self.config = config = config or tg.config._current_obj()
        self.globals = config.get('tg.app_globals')
        self.package_name = config['package_name']
        self.lang = config.get('i18n.lang')

        if self.lang is None:
            backward_compatible_lang = config.get('lang')
            if backward_compatible_lang:
                warnings.warn('"lang" option has been renamed to "i18n.lang" and '
                              'will be removed in next major version.', DeprecationWarning)
                self.lang = backward_compatible_lang

        self.controller_classes = {}
        self.controller_instances = {}

        # Cache some options for use during requests
        self.strict_tmpl_context = self.config['tg.strict_tmpl_context']
        self.pylons_compatible = self.config.get('tg.pylons_compatible', True)
        self.enable_routes = self.config.get('enable_routes', False)

        self.resp_options = config.get('tg.response_options',
                                       dict(content_type='text/html',
                                            charset='utf-8',
                                            headers={'Cache-Control': 'no-cache',
                                                     'Pragma': 'no-cache',
                                                     'Content-Type': None,
                                                     'Content-Length': '0'}))

        self.wrapped_dispatch = self.dispatch
        for wrapper in self.config.get('application_wrappers', []):
            try:
                app_wrapper = wrapper(self.wrapped_dispatch, self.config)
                if getattr(app_wrapper, 'injected', True):
                    # if it conforms to the ApplicationWrapper ABC inject it only
                    # when an injected=True property is provided.
                    self.wrapped_dispatch = app_wrapper

                    # Force resolution of @cached_property, this speeds up requests
                    # and also acts as a prevention against race conditions on the
                    # property itself.
                    getattr(app_wrapper, 'next_handler', None)

            except TypeError:
                #backward compatibility with wrappers that didn't receive the config
                self.wrapped_dispatch = wrapper(self.wrapped_dispatch)

        if 'tg.root_controller' in self.config:
            self.controller_instances['root'] = self.config['tg.root_controller']

    def setup_pylons_compatibility(self, environ, controller): #pragma: no cover
        """Updates environ to be backward compatible with Pylons"""
        try:
            environ['pylons.controller'] = controller
            environ['pylons.pylons'] = environ['tg.locals']

            self.config['pylons.app_globals'] = self.globals

            pylons.request = request_local.request
            pylons.cache = request_local.cache
            pylons.config = request_local.config
            pylons.app_globals = request_local.app_globals
            pylons.session = request_local.session
            pylons.translator = request_local.translator
            pylons.response = request_local.response
            pylons.tmpl_context = request_local.tmpl_context

            if self.enable_routes:
                environ['pylons.routes_dict'] = environ['tg.routes_dict']
                pylons.url = request_local.url
        except ImportError:
            pass

    def __call__(self, environ, start_response):
        # Hide outer middlewares when crash inside application itself
        __traceback_hide__ = 'before'

        testmode, context, registry = self.setup_app_env(environ)

        # Expose a path that simply registers the globals and preserves them
        # without doing much else
        if testmode is True and environ['PATH_INFO'] == '/_test_vars':
            registry.preserve(force=True)
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ['DONE'.encode('utf-8')]

        controller = self.resolve(environ, context)
        response = self.wrapped_dispatch(controller, environ, context)

        if testmode is True:
            environ['paste.testing_variables']['response'] = response

        try:
            if response is not None:
                return response(environ, start_response)

            raise Exception("No content returned by controller (Did you "
                            "remember to 'return' it?) in: %r" %
                            controller)
        finally:
            # Help Python collect ram a bit faster by removing the reference
            # cycle that the thread local objects cause
            del environ['tg.locals']
            if has_pylons and 'pylons.pylons' in environ: #pragma: no cover
                del environ['pylons.pylons']

    def setup_app_env(self, environ):
        """Setup Request, Response and TurboGears context objects.

        Is also in charge of pushing TurboGears context into the
        paste registry and detect test mode. Returns whenever
        the testmode is enabled or not and the TurboGears context.
        """
        conf = self.config
        testing = False

        # Setup the basic global objects
        req = Request(environ)
        req._fast_setattr('_language', self.lang)
        req._fast_setattr('_response_type', None)

        resp_options = self.resp_options
        response = Response(
            content_type=resp_options['content_type'],
            charset=resp_options['charset'],
            headers=resp_options['headers']
        )

        # Setup the translator object
        translator = _get_translator(self.lang, tg_config=conf)

        if self.strict_tmpl_context:
            tmpl_context = TemplateContext()
        else:
            tmpl_context = AttribSafeTemplateContext()

        app_globals = self.globals

        locals = RequestLocals()
        locals.response = response
        locals.request = req
        locals.app_globals = app_globals
        locals.config = conf
        locals.tmpl_context = tmpl_context
        locals.translator = translator
        locals.session = environ.get('beaker.session')  # Usually None, unless middleware in place
        locals.cache = environ.get('beaker.cache')  # Usually None, unless middleware in place

        if self.enable_routes: #pragma: no cover
            url = environ.get('routes.url')
            locals.url = url

        environ['tg.locals'] = locals

        # Register Global objects
        registry = environ['paste.registry']
        registry.register(request_local.config, conf)
        registry.register(request_local.context, locals)

        if 'paste.testing_variables' in environ:
            testing = True
            testenv = environ['paste.testing_variables']
            testenv['req'] = req
            testenv['response'] = response
            testenv['tmpl_context'] = tmpl_context
            testenv['app_globals'] = self.globals
            testenv['config'] = conf
            testenv['session'] = locals.session
            testenv['cache'] = locals.cache

        return testing, locals, registry

    def resolve(self, environ, context):
        """Uses dispatching information found in
        ``environ['wsgiorg.routing_args']`` to retrieve a controller
        name and return the controller instance from the appropriate
        controller module.

        Override this to change how the controller name is found and
        returned.

        """
        if self.enable_routes: #pragma: no cover
            match = environ['wsgiorg.routing_args'][1]
            environ['tg.routes_dict'] = match
            controller = match.get('controller')
            if not controller:
                return None
        else:
            controller = 'root'

        return self.get_controller_instance(controller)

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

    def get_controller_instance(self, controller):
        # Check to see if we've cached the instance for this name
        try:
            return self.controller_instances[controller]
        except KeyError:
            mycontroller = self.find_controller(controller)

            # If it's a class, instantiate it
            if hasattr(mycontroller, '__bases__'):
                mycontroller = mycontroller()

            self.controller_instances[controller] = mycontroller
            return mycontroller

    def dispatch(self, controller, environ, context):
        """Dispatches to a controller, the controller itself is expected
        to implement the routing system.

        Override this to change how requests are dispatched to controllers.
        """
        if not controller:
            return HTTPNotFound()

        #Setup pylons compatibility before calling controller
        if has_pylons and self.pylons_compatible: #pragma: no cover
            self.setup_pylons_compatibility(environ, controller)

        # Controller is assumed to accept WSGI Environ and TG Context
        # and return a Response object.
        return controller(environ, context)


class TemplateContext(object):
    """Used by TurboGears as ``tg.tmpl_context``.

    It's just a plain python object with an improved representation
    to show all the attributes currently available into the object.

    """
    def __repr__(self):
        attrs = sorted((name, value)
                       for name, value in self.__dict__.items()
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

    def __getattr__(self, item):
        if item in ('form_values', 'form_errors'):
            warnings.warn('tmpl_context.form_values and tmpl_context.form_errors got deprecated '
                          'use request.validation instead', DeprecationWarning)
            return tg.request.validation[item[5:]]
        elif item == 'controller_url':
            warnings.warn('tmpl_context.controller_url got deprecated, '
                          'use request.controller_url instead', DeprecationWarning)
            return tg.request.controller_url

        raise AttributeError()


class AttribSafeTemplateContext(TemplateContext):
    """The ``tg.tmpl_context`` object, with lax attribute access (
    returns '' when the attribute does not exist)"""
    def __getattr__(self, name):
        try:
            return TemplateContext.__getattr__(self, name)
        except AttributeError:
            return ''
