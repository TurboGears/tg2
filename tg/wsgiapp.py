import os, sys, logging
import warnings
import inspect
from webob.exc import HTTPNotFound

import tg
from tg import request_local
from tg.configuration.utils import TGConfigError
from tg.i18n import _get_translator
from tg.request_local import Request, Response

log = logging.getLogger(__name__)


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

        self.controller_classes = {}
        self.controller_instances = {}

        # Cache some options for use during requests
        self.strict_tmpl_context = self.config['tg.strict_tmpl_context']

        self.resp_options = config.get('tg.response_options',
                                       dict(content_type='text/html',
                                            charset='utf-8',
                                            headers={'Cache-Control': 'no-cache',
                                                     'Pragma': 'no-cache',
                                                     'Content-Type': None,
                                                     'Content-Length': '0'}))

        self.wrapped_dispatch = self._dispatch
        for __, wrapper in self.config.get('application_wrappers', []):
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
                # backward compatibility with wrappers that didn't receive the config
                self.wrapped_dispatch = wrapper(self.wrapped_dispatch)

        if self.config.get('tg.root_controller') is not None:
            self.controller_instances['root'] = self.config['tg.root_controller']

    def __call__(self, environ, start_response):
        """Serve a WSGI Request"""
        # Hide outer middlewares when crash inside application itself
        __traceback_hide__ = 'before'

        testmode, context, registry = self._setup_app_env(environ)

        # Expose a path that simply registers the globals and preserves them
        # without doing much else
        if testmode is True and environ['PATH_INFO'] == '/_test_vars':
            registry.preserve(force=True)
            start_response('200 OK', [('Content-type', 'text/plain')])
            return ['DONE'.encode('utf-8')]

        controller = self._get_controller_instance('root')
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

    def _setup_app_env(self, environ):
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

    @classmethod
    def class_name_from_module_name(cls, module_name):
        words = module_name.replace('-', '_').split('_')
        return ''.join(w.title() for w in words)

    @classmethod
    def lookup_controller(cls, config, controller):
        """Locates a controller by attempting to import it then grab
        the SomeController instance from the imported module.

        Override this to change how the controller object is found once
        the URL has been resolved.

        :param dict config: The configuration options for the application,
         usually this will be ``tg.config``.
        :param str controller: The controller name, this will be the name
         of the python module containing the controller.

        """
        root_module_path = config['paths']['root']
        base_controller_path = config['paths']['controllers']
        if base_controller_path is None:
            raise TGConfigError('Unable to load controllers, no controllers path configured!')

        # remove the part of the path we expect to be the root part (plus one '/')
        assert base_controller_path.startswith(root_module_path)
        controller_path = base_controller_path[len(root_module_path)+1:]

        # attach the package
        full_module_name = '.'.join([config['package_name']] +
                                    controller_path.split(os.sep) +
                                    controller.split('/'))

        # Hide the traceback here if the import fails (bad syntax and such)
        __traceback_hide__ = 'before_and_this'

        __import__(full_module_name)
        module_name = controller.split('/')[-1]
        class_name = cls.class_name_from_module_name(module_name) + 'Controller'
        return getattr(sys.modules[full_module_name], class_name)

    def find_controller(self, controller):
        """Locates a controller for this TGApp.

        This is the same af :meth:`.lookup_controller` but will reuse
        configuration of the application and will cache results.

        :param str controller: The controller name, this will be the name
         of the python module containing the controller.
        """
        # Check to see if we've cached the class instance for this name
        if controller in self.controller_classes:
            return self.controller_classes[controller]

        mycontroller = self.lookup_controller(self.config, controller)

        self.controller_classes[controller] = mycontroller
        return mycontroller

    def _get_controller_instance(self, controller):
        # Check to see if we've cached the instance for this name
        try:
            return self.controller_instances[controller]
        except KeyError:
            mycontroller = self.find_controller(controller)

            # If it's a class, instantiate it
            if inspect.isclass(mycontroller):
                mycontroller = mycontroller()

            self.controller_instances[controller] = mycontroller
            return mycontroller

    def _dispatch(self, controller, environ, context):
        """Dispatches to a controller, the controller itself is expected
        to implement the routing system.
        """
        if not controller:
            return HTTPNotFound()

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
            return getattr(tg.request.validation, item[5:])
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
