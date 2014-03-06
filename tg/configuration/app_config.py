"""Configuration Helpers for TurboGears 2"""

import atexit
import os
import logging
import warnings
from copy import copy, deepcopy
import mimetypes
from collections import MutableMapping as DictMixin, deque

from tg.i18n import ugettext, get_lang

from tg.support.middlewares import SessionMiddleware, CacheMiddleware
from tg.support.middlewares import StaticsMiddleware, SeekableRequestBodyMiddleware, \
    DBSessionRemoverMiddleware
from tg.support.registry import RegistryManager
from tg.support.converters import asbool, asint
from tg.request_local import config as reqlocal_config

import tg
from tg.configuration.utils import coerce_config
from tg.util import Bunch, get_partial_dict, DottedFileNameFinder, call_controller
from tg.configuration import milestones
from tg.configuration.utils import TGConfigError

from tg.renderers.genshi import GenshiRenderer
from tg.renderers.json import JSONRenderer
from tg.renderers.jinja import JinjaRenderer
from tg.renderers.mako import MakoRenderer
from tg.renderers.kajiki import KajikiRenderer

log = logging.getLogger(__name__)


class DispatchingConfigWrapper(DictMixin):
    """Wrapper for the Dispatching configuration.

    Simple wrapper for the DispatchingConfig object that provides attribute
    style access to the Pylons config dictionary.

    This class works by proxying all attribute and dictionary access to
    the underlying DispatchingConfig config object, which is an application local
    proxy that allows for multiple TG2 applications to live
    in the same process simultaneously, but to always get the right
    config data for the application that's requesting them.

    Sites, with seeking to maximize needs may prefer to use the Pylons
    config stacked object proxy directly, using just dictionary style
    access, particularly whenever config is checked on a per-request basis.

    """

    def __init__(self, dict_to_wrap):
        """Initialize the object by passing in config to be wrapped"""
        self.__dict__['config_proxy'] = dict_to_wrap

    def __getitem__(self, key):
        return  self.config_proxy.current_conf()[key]

    def __setitem__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __getattr__(self, key):
        """Our custom attribute getter.

        Tries to get the attribute off the wrapped object first,
        if that does not work, tries dictionary lookup, and finally
        tries to grab all keys that start with the attribute and
        return sub-dictionaries that can be looked up.

        """
        try:
            return self.config_proxy.__getattribute__(key)
        except AttributeError:
            try:
                return self.config_proxy.current_conf()[key]
            except KeyError:
                return get_partial_dict(key, self.config_proxy.current_conf())

    def __setattr__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __delattr__(self, name):
        try:
            del self.config_proxy.current_conf()[name]
        except KeyError:
            raise AttributeError(name)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __len__(self):
        return len(self.config_proxy.current_conf())

    def __iter__(self):
        return iter(self.config_proxy.current_conf())

    def __repr__(self):
        return repr(self.config_proxy.current_conf())

    def keys(self):
        return self.config_proxy.keys()


defaults = {
    'debug': False,
    'package': None,
    'paths': {'root': None,
              'controllers': None,
              'templates': ['.'],
              'static_files': None},
    'tg.app_globals': None,
    'tg.strict_tmpl_context': True,
    'tg.pylons_compatible': True,
    'lang': None
}

# Push an empty config so all accesses to config at import time have something
# to look at and modify. This config will be merged with the app's when it's
# built in the paste.app_factory entry point.
reqlocal_config.push_process_config(deepcopy(defaults))

#Create a config object that has attribute style lookup built in.
config = DispatchingConfigWrapper(reqlocal_config)


class AppConfig(Bunch):
    """Class to store application configuration.

    This class should have configuration/setup information
    that is *necessary* for proper application function.
    Deployment specific configuration information should go in
    the config files (e.g. development.ini or deployment.ini).

    AppConfig instances have a number of methods that are meant to be
    overridden by users who wish to have finer grained control over
    the setup of the WSGI environment in which their application is run.

    This is the place to configure custom routes, transaction handling,
    error handling, etc.

    """

    def __init__(self, minimal=False, root_controller=None):
        """Creates some configuration defaults"""

        # Create a few bunches we know we'll use
        self.paths = Bunch()

        # Provide a default app_globals for single file applications
        self['tg.app_globals'] = Bunch({'dotted_filename_finder':DottedFileNameFinder()})

        # And also very often...
        self.sa_auth = Bunch()

        #Set individual defaults
        self.auto_reload_templates = True
        self.auth_backend = None
        self.stand_alone = True

        self.renderers = []
        self.default_renderer = 'genshi'
        self.render_functions = Bunch()
        self.rendering_engines = {}
        self.rendering_engines_without_vars = set()
        self.rendering_engines_options = {}

        self.enable_routes = False
        self.enable_routing_args = False
        self.disable_request_extensions = minimal

        self.use_ming = False
        self.use_sqlalchemy = False
        self.use_transaction_manager = not minimal
        self.commit_veto = None
        self.use_toscawidgets = not minimal
        self.use_toscawidgets2 = False
        self.prefer_toscawidgets2 = False
        self.use_dotted_templatenames = not minimal
        self.handle_error_page = not minimal
        self.registry_streaming = True

        self.use_sessions = not minimal
        self.i18n_enabled = not minimal
        self.serve_static = not minimal

        # Registry for functions to be called on startup/teardown
        self.call_on_startup = []
        self.call_on_shutdown = []
        self.controller_caller = call_controller
        self.controller_wrappers = []
        self.dedicated_controller_wrappers = {}
        self.application_wrappers = []
        self.application_wrappers_dependencies = {False: [],
                                                  None: []}
        self.hooks = dict(before_validate=[],
                          before_call=[],
                          before_render=[],
                          after_render=[],
                          before_render_call=[],
                          after_render_call=[],
                          before_config=[],
                          after_config=[])

        # The codes TG should display an error page for. All other HTTP errors are
        # sent to the client or left for some middleware above us to handle
        self.handle_status_codes = [403, 404]

        #override this variable to customize how the tw2 middleware is set up
        self.custom_tw2_config = {}

        #This is for minimal mode to set root controller manually
        if root_controller is not None:
            self['tg.root_controller'] = root_controller

        self.register_rendering_engine(JSONRenderer)
        self.register_rendering_engine(GenshiRenderer)
        self.register_rendering_engine(MakoRenderer)
        self.register_rendering_engine(JinjaRenderer)
        self.register_rendering_engine(KajikiRenderer)

    def get_root_module(self):
        root_module_path = self.paths['root']
        if not root_module_path:
            return None

        base_controller_path = self.paths['controllers']
        controller_path = base_controller_path[len(root_module_path)+1:]
        root_controller_module = '.'.join([self.package_name] + controller_path.split(os.sep) + ['root'])
        return root_controller_module

    def register_hook(self, hook_name, func):
        warnings.warn("AppConfig.register_hook is deprecated, "
                      "please use tg.hooks.register and "
                      "tg.hooks.wrap_controller instead", DeprecationWarning)

        if hook_name == 'controller_wrapper':
            tg.hooks.wrap_controller(func)
        else:
            tg.hooks.register(hook_name, func)

    def register_wrapper(self, wrapper, after=None):
        """Registers a TurboGears application wrapper.

        Application wrappers are like WSGI middlewares but
        are executed in the context of TurboGears and work
        with abstractions like Request and Respone objects.

        Application wrappers are callables built by passing
        the next handler in chain and the current TurboGears
        configuration.

        Every wrapper, when called, is expected to accept
        the WSGI environment and a TurboGears context as parameters
        and are expected to return a :class:`tg.request_local.Response`
        instance::

            class AppWrapper(object):
                def __init__(self, handler, config):
                    self.handler = handler

                def __call__(self, environ, context):
                    print 'Going to run %s' % context.request.path
                    return self.handler(environ, context)
        """
        if milestones.environment_loaded.reached:
            # We must block registering wrappers if milestone passed, this is because
            # wrappers are consumed by TGApp constructor, and all the hooks available
            # after the milestone and that could register new wrappers are actually
            # called after TGApp constructors and so the wrappers wouldn't be applied.
            raise TGConfigError('Cannot register application wrappers after application '
                                'environment has already been loaded')

        self.application_wrappers_dependencies.setdefault(after, []).append(wrapper)
        milestones.environment_loaded.register(self._configure_application_wrappers)

    def register_rendering_engine(self, factory):
        """Registers a rendering engine ``factory``.

        Rendering engine factories are :class:`tg.renderers.base.RendererFactory`
        subclasses in charge of creating a rendering engine.

        """
        for engine, options in factory.engines.items():
            self.rendering_engines[engine] = factory
            self.rendering_engines_options[engine] = options
            if factory.with_tg_vars is False:
                self.rendering_engines_without_vars.add(engine)

    def _setup_startup_and_shutdown(self):
        for cmd in self.call_on_startup:
            if callable(cmd):
                try:
                    cmd()
                except Exception as error:
                    log.exception("Error registering %s at startup: %s" % (cmd, error ))
            else:
                log.warn("Unable to register %s for startup" % cmd )

        for cmd in self.call_on_shutdown:
            if callable(cmd):
                atexit.register(cmd)
            else:
                log.warn("Unable to register %s for shutdown" % cmd )

    def _configure_application_wrappers(self):
        visit_queue = deque([False, None])
        while visit_queue:
            current = visit_queue.popleft()
            if current not in (False, None):
                self.application_wrappers.append(current)

            dependant_wrappers = self.application_wrappers_dependencies.pop(current, [])
            visit_queue.extendleft(reversed(dependant_wrappers))

    def _configure_package_paths(self):
        root = os.path.dirname(os.path.abspath(self.package.__file__))
        # The default paths:
        paths = Bunch(root=root,
                     controllers=os.path.join(root, 'controllers'),
                     static_files=os.path.join(root, 'public'),
                     templates=[os.path.join(root, 'templates')])
        # If the user defined custom paths, then use them instead of the
        # default ones:
        paths.update(self.paths)
        self.paths = paths

    def _init_config(self, global_conf, app_conf):
        """Initialize the config object.

        Besides basic initialization, this method copies all the values
        in base_config into the ``tg.config`` objects.

        """
        # Load the mimetypes with its default types
        self.mimetypes = mimetypes.MimeTypes()

        try:
            self.package_name = self.package.__name__
        except AttributeError:
            self.package_name = None

        log.debug("Initializing configuration, package: '%s'", self.package_name)
        conf = global_conf.copy()
        conf.update(app_conf)
        conf.update(dict(app_conf=app_conf, global_conf=global_conf))
        conf.update(self.pop('environment_load', {}))
        conf['paths'] = self.paths
        conf['package_name'] = self.package_name
        conf['debug'] = asbool(conf.get('debug'))

        # Ensure all the keys from defaults are present, load them if not
        for key, val in deepcopy(defaults).items():
            conf.setdefault(key, val)

        # Ensure all paths are set, load default ones otherwise
        for key, val in defaults['paths'].items():
            conf['paths'].setdefault(key, val)

        # Load the errorware configuration from the Paste configuration file
        # These all have defaults, and emails are only sent if configured and
        # if this application is running in production mode
        errorware = {}
        errorware['debug'] = conf['debug']
        if not errorware['debug']:
            errorware['debug'] = False

            trace_errors_config = coerce_config(conf, 'trace_errors.', {'smtp_use_tls': asbool,
                                                                        'dump_request_size': asint,
                                                                        'dump_request': asbool,
                                                                        'dump_local_frames': asbool,
                                                                        'dump_local_frames_count': asint})
            if not trace_errors_config:
                # backward compatibility
                warnings.warn("direct usage of error tracing options has been deprecated, "
                              "please specify them as trace_errors.option_name instad of directly "
                              "setting option_name. EXAMPLE: trace_errors.error_email", DeprecationWarning)

                trace_errors_config['error_email'] = conf.get('email_to')
                trace_errors_config['error_log'] = conf.get('error_log', None)
                trace_errors_config['smtp_server'] = conf.get('smtp_server', 'localhost')
                trace_errors_config['smtp_use_tls'] = asbool(conf.get('smtp_use_tls', False))
                trace_errors_config['smtp_username'] = conf.get('smtp_username')
                trace_errors_config['smtp_password'] = conf.get('smtp_password')
                trace_errors_config['error_subject_prefix'] = conf.get('error_subject_prefix', 'WebApp Error: ')
                trace_errors_config['from_address'] = conf.get('from_address', conf.get('error_email_from', 'turbogears@yourapp.com'))
                trace_errors_config['error_message'] = conf.get('error_message', 'An internal server error occurred')
            else:
                # Provide Defaults
                trace_errors_config.setdefault('error_subject_prefix',
                                               'WebApp Error: ')
                trace_errors_config.setdefault('error_message',
                                               'An internal server error occurred')

            errorware.update(trace_errors_config)

        conf['tg.errorware'] = errorware

        # Copy in some defaults
        if 'cache_dir' in conf:
            conf.setdefault('beaker.session.data_dir', os.path.join(conf['cache_dir'], 'sessions'))
            conf.setdefault('beaker.cache.data_dir', os.path.join(conf['cache_dir'], 'cache'))
        conf['tg.cache_dir'] = conf.pop('cache_dir', conf['app_conf'].get('cache_dir'))

        if self.prefer_toscawidgets2:
            self.use_toscawidgets = False
            self.use_toscawidgets2 = True

        if not self.use_sqlalchemy:
            #Transaction manager is useless with Ming
            self.use_transaction_manager = False

        # Load conf dict into the global config object
        config.update(conf)

        if 'auto_reload_templates' in config:
            self.auto_reload_templates = asbool(config['auto_reload_templates'])

        config['application_root_module'] = self.get_root_module()
        if conf['paths']['root']:
            self.localedir = os.path.join(conf['paths']['root'], 'i18n')
        else:
            self.i18n_enabled = False

        if not conf['paths']['static_files']:
            self.serve_static = False

        self._configure_renderers()

        config.update(self)

        #see http://trac.turbogears.org/ticket/2247
        if asbool(config['debug']):
            config['tg.strict_tmpl_context'] = True
        else:
            config['tg.strict_tmpl_context'] = False

        self.after_init_config()
        self._configure_mimetypes()

        milestones.config_ready.reach()

    def _configure_renderers(self):
        """Provides default configurations for renderers"""
        if not 'json' in self.renderers:
            self.renderers.append('json')

        if self.default_renderer not in self.renderers:
            first_renderer = self.renderers[0]
            log.warn('Default renderer not in renders, automatically switching to %s' % first_renderer)
            self.default_renderer = first_renderer

    def _configure_mimetypes(self):
        lookup = {'.json': 'application/json',
                  '.js': 'application/javascript'}
        lookup.update(config.get('mimetype_lookup', {}))

        for key, value in lookup.items():
            self.mimetypes.add_type(value, key)

    def after_init_config(self):
        """
        Override this method to set up configuration variables at the application
        level.  This method will be called after your configuration object has
        been initialized on startup.  Here is how you would use it to override
        the default setting of tg.strict_tmpl_context ::

            from tg.configuration import AppConfig
            from tg import config

            class MyAppConfig(AppConfig):
                def after_init_config(self):
                    config['tg.strict_tmpl_context'] = False

            base_config = MyAppConfig()

        """

    def setup_routes(self):
        """Setup the default TG2 routes

        Override this and setup your own routes maps if you want to use
        custom routes.

        It is recommended that you keep the existing application routing in
        tact, and just add new connections to the mapper above the routes_placeholder
        connection.  Lets say you want to add a tg controller SamplesController,
        inside the controllers/samples.py file of your application.  You would
        augment the app_cfg.py in the following way::

            from routes import Mapper
            from tg.configuration import AppConfig

            class MyAppConfig(AppConfig):
                def setup_routes(self):
                    map = Mapper(directory=config['paths']['controllers'],
                                always_scan=config['debug'])

                    # Add a Samples route
                    map.connect('/samples/', controller='samples', action=index)

                    # Setup a default route for the root of object dispatch
                    map.connect('*url', controller='root', action='routes_placeholder')

                    config['routes.map'] = map


            base_config = MyAppConfig()

        """
        if not self.enable_routes:
            return None

        from routes import Mapper

        map = Mapper(directory=config['paths']['controllers'],
                     always_scan=config['debug'])

        # Setup a default route for the root of object dispatch
        map.connect('*url', controller='root', action='routes_placeholder')

        config['routes.map'] = map
        return map

    def setup_helpers_and_globals(self):
        """Add helpers and globals objects to the config.

        Override this method to customize the way that ``app_globals``
        and ``helpers`` are setup.

        """

        try:
            g = self.package.lib.app_globals.Globals()
        except AttributeError:
            log.warn('Application has a package but no lib.app_globals.Globals class is available.')
            return

        g.dotted_filename_finder = DottedFileNameFinder()
        config['tg.app_globals'] = g

        if config.get('tg.pylons_compatible', True):
            config['pylons.app_globals'] = g

    def setup_persistence(self):
        """Override this method to define how your application configures it's persistence model.
           the default is to setup sqlalchemy from the cofiguration file, but you might choose
           to set up a persistence system other than sqlalchemy, or add an additional persistence
           layer.  Here is how you would go about setting up a ming (mongo) persistence layer::

            class MingAppConfig(AppConfig):
                def setup_persistence(self):
                    self.ming_ds = DataStore(config['mongo.url'])
                    session = Session.by_name('main')
                    session.bind = self.ming_ds
        """
        if self.use_sqlalchemy:
            self.setup_sqlalchemy()
        elif self.use_ming:
            self.setup_ming()

    def setup_ming(self):
        """Setup MongoDB database engine using Ming"""
        try:
            from ming import create_datastore
            def create_ming_datastore(url, database, **kw):
                if database and url[-1] != '/':
                    url += '/'
                ming_url = url + database
                return create_datastore(ming_url, **kw)
        except ImportError: #pragma: no cover
            from ming.datastore import DataStore
            def create_ming_datastore(url, database, **kw):
                return DataStore(url, database=database, **kw)

        def mongo_read_pref(value):
            from pymongo.read_preferences import ReadPreference
            return getattr(ReadPreference, value)

        datastore_options = coerce_config(config, 'ming.connection.', {'max_pool_size':asint,
                                                                       'network_timeout':asint,
                                                                       'tz_aware':asbool,
                                                                       'safe':asbool,
                                                                       'journal':asbool,
                                                                       'wtimeout':asint,
                                                                       'fsync':asbool,
                                                                       'ssl':asbool,
                                                                       'read_preference':mongo_read_pref})
        datastore_options.pop('host', None)
        datastore_options.pop('port', None)

        datastore = create_ming_datastore(config['ming.url'], config.get('ming.db', ''), **datastore_options)
        config['pylons.app_globals'].ming_datastore = datastore
        self.package.model.init_model(datastore)

    def setup_sqlalchemy(self):
        """Setup SQLAlchemy database engine.

        The most common reason for modifying this method is to add
        multiple database support.  To do this you might modify your
        app_cfg.py file in the following manner::

            from tg.configuration import AppConfig, config
            from myapp.model import init_model

            # add this before base_config =
            class MultiDBAppConfig(AppConfig):
                def setup_sqlalchemy(self):
                    '''Setup SQLAlchemy database engine(s)'''
                    from sqlalchemy import engine_from_config
                    engine1 = engine_from_config(config, 'sqlalchemy.first.')
                    engine2 = engine_from_config(config, 'sqlalchemy.second.')
                    # engine1 should be assigned to sa_engine as well as your first engine's name
                    config['tg.app_globals'].sa_engine = engine1
                    config['tg.app_globals'].sa_engine_first = engine1
                    config['tg.app_globals'].sa_engine_second = engine2
                    # Pass the engines to init_model, to be able to introspect tables
                    init_model(engine1, engine2)

            #base_config = AppConfig()
            base_config = MultiDBAppConfig()

        This will pull the config settings from your .ini files to create the necessary
        engines for use within your application.  Make sure you have a look at :ref:`multidatabase`
        for more information.

        """
        from sqlalchemy import engine_from_config

        balanced_master = config.get('sqlalchemy.master.url')
        if not balanced_master:
            engine = engine_from_config(config, 'sqlalchemy.')
        else:
            engine = engine_from_config(config, 'sqlalchemy.master.')
            config['balanced_engines'] = {'master':engine,
                                          'slaves':{},
                                          'all':{'master':engine}}

            all_engines = config['balanced_engines']['all']
            slaves = config['balanced_engines']['slaves']
            for entry in config.keys():
                if entry.startswith('sqlalchemy.slaves.'):
                    slave_path = entry.split('.')
                    slave_name = slave_path[2]
                    if slave_name == 'master':
                        raise TGConfigError('A slave node cannot be named master')
                    slave_config = '.'.join(slave_path[:3])
                    all_engines[slave_name] = slaves[slave_name] = engine_from_config(config, slave_config+'.')

            if not config['balanced_engines']['slaves']:
                raise TGConfigError('When running in balanced mode your must specify at least a slave node')

        # Pass the engine to initmodel, to be able to introspect tables
        config['tg.app_globals'].sa_engine = engine
        self.package.model.init_model(engine)

        if not hasattr(self, 'DBSession'):
            # If the user hasn't specified a scoped_session, assume
            # he/she uses the default DBSession in model
            model = getattr(self, 'model', self.package.model)
            self.DBSession = model.DBSession

    def setup_auth(self):
        """
        Override this method to define how you would like the authentication options
        to be setup for your application.
        """
        if hasattr(self, 'setup_sa_auth_backend'):
            warnings.warn("setup_sa_auth_backend is deprecated, please override"
                          "AppConfig.setup_auth instead", DeprecationWarning)
            self.setup_sa_auth_backend()
        elif self.auth_backend in ("ming", "sqlalchemy"):
            if 'beaker.session.secret' not in config:
                raise TGConfigError("You must provide a value for 'beaker.session.secret' "
                                    "If this is a project quickstarted with TG 2.0.2 or earlier "
                                    "double check that you have base_config['beaker.session.secret'] "
                                    "= 'mysecretsecret' in your app_cfg.py file.")

            # The developer must have defined a 'sa_auth' section, because
            # values such as the User, Group or Permission classes must be
            # explicitly defined.
            self.sa_auth.setdefault('form_plugin', None)
            self.sa_auth.setdefault('cookie_secret', config['beaker.session.secret'])

    def _setup_controller_wrappers(self):
        base_controller_caller = config.get('controller_caller')

        controller_caller = base_controller_caller
        for wrapper in self.get('controller_wrappers', []):
            controller_caller = wrapper(self, controller_caller)
        config['controller_caller'] = controller_caller

        dedicated_wrappers = config.get('dedicated_controller_wrappers', {})
        for wrapped_controller in dedicated_wrappers:
            controller_caller = base_controller_caller
            wrappers = dedicated_wrappers[wrapped_controller]
            # Apply custom wrappers for controller
            for wrapper in wrappers:
                controller_caller = wrapper(self, controller_caller)
            # Apply generic wrappers for application
            for wrapper in self.get('controller_wrappers', []):
                controller_caller = wrapper(self, controller_caller)
            dedicated_wrappers[wrapped_controller] = controller_caller

    def _setup_renderers(self):
        for renderer in self.renderers[:]:
            setup = getattr(self, 'setup_%s_renderer'%renderer, None)
            if setup is not None:
                # Backward compatible old-way of configuring rendering engines
                warnings.warn("Using setup_NAME_renderer to configure rendering engines"
                              "is now deprecated, please use register_rendering_engine "
                              "with a tg.renderers.base.RendererFactory subclass instead",
                              DeprecationWarning, stacklevel=2)

                success = setup()
                if success is False:
                    log.error('Failed to initialize %s template engine, removing it...' % renderer)
                    self.renderers.remove(renderer)
            elif renderer in self.rendering_engines:
                rendering_engine = self.rendering_engines[renderer]
                engines = rendering_engine.create(config, config['tg.app_globals'])
                if engines is None:
                    log.error('Failed to initialize %s template engine, removing it...' % renderer)
                    self.renderers.remove(renderer)
                else:
                    self.render_functions.update(engines)
            else:
                raise TGConfigError('This configuration object does not support the %s renderer' % renderer)

        milestones.renderers_ready.reach()

    def make_load_environment(self):
        """Return a load_environment function.

        The returned load_environment function can be called to configure
        the TurboGears runtime environment for this particular application.
        You can do this dynamically with multiple nested TG applications
        if necessary.

        """

        def load_environment(global_conf, app_conf):
            """Configure the TurboGears environment via ``tg.configuration.config``."""
            global_conf = Bunch(global_conf)
            app_conf = Bunch(app_conf)

            try:
                app_package = self.package
            except AttributeError:
                #if we don't have a specified package, don't try
                #to detect paths and helpers from the package.
                #Expect the user to specify them.
                app_package = None

            if app_package:
                self._configure_package_paths()

            self._init_config(global_conf, app_conf)

            #Registers functions to be called at startup and shutdown
            #from self.call_on_startup and shutdown respectively.
            self._setup_startup_and_shutdown()

            self.setup_routes()

            if app_package:
                self.setup_helpers_and_globals()

            self.setup_auth()
            self._setup_renderers()
            self.setup_persistence()

            # Trigger milestone here so that it gets triggered even when
            # websetup (setup-app command) is performed.
            milestones.environment_loaded.reach()

        return load_environment

    def add_error_middleware(self, global_conf, app):
        """Add middleware which handles errors and exceptions."""
        from tg.error import ErrorReporter
        app = ErrorReporter(app, global_conf, **config['tg.errorware'])

        if self.handle_error_page:
            from tg.support.middlewares import StatusCodeRedirect

            # Display error documents for self.handle_status_codes status codes (and
            # 500 when debug is disabled)
            if asbool(config['debug']):
                app = StatusCodeRedirect(app, self.handle_status_codes)
            else:
                app = StatusCodeRedirect(app, self.handle_status_codes + [500])

        return app

    def add_debugger_middleware(self, global_conf, app):
        from tg.error import ErrorHandler
        return ErrorHandler(app, global_conf)

    def add_auth_middleware(self, app, skip_authentication):
        """
        Configure authentication and authorization.

        :param app: The TG2 application.
        :param skip_authentication: Should authentication be skipped if
            explicitly requested? (used by repoze.who-testutil)
        :type skip_authentication: bool

        """
        # Start with the current configured authentication options.
        # Depending on the auth backend a new auth_args dictionary
        # can replace this one later on.
        auth_args = copy(self.sa_auth)

        # Configuring auth logging:
        if 'log_stream' not in self.sa_auth:
            auth_args['log_stream'] = logging.getLogger('auth')

        # Removing keywords not used by repoze.who:
        auth_args.pop('password_encryption_method', None)

        if not skip_authentication and 'cookie_secret' not in auth_args:
            raise TGConfigError("base_config.sa_auth.cookie_secret is required "
                                "you must define it in app_cfg.py or set "
                                "sa_auth.cookie_secret in development.ini")

        if 'authmetadata' not in auth_args: #pragma: no cover
            # authmetadata not provided, fallback to old authentication setup
            if self.auth_backend == "sqlalchemy":
                from repoze.what.plugins.quickstart import setup_sql_auth
                app = setup_sql_auth(app, skip_authentication=skip_authentication, **auth_args)
            elif self.auth_backend == "ming":
                from tgming import setup_ming_auth
                app = setup_ming_auth(app, skip_authentication=skip_authentication, **auth_args)
        else:
            try:
                pos = auth_args['authenticators'].index(('default', None))
            except KeyError:
                # Didn't specify authenticators, setup default one
                pos = None
            except ValueError:
                # Specified authenticators and default is not in there
                # so we want to skip default TG auth configuration.
                pos = -1

            if pos is None or pos >= 0:
                if getattr(auth_args['authmetadata'], 'authenticate', None) is not None:
                    from tg.configuration.auth import create_default_authenticator
                    auth_args, tgauth = create_default_authenticator(**auth_args)
                    authenticator = ('tgappauth', tgauth)
                elif self.auth_backend == "sqlalchemy":
                    from tg.configuration.sqla.auth import create_default_authenticator
                    auth_args, sqlauth = create_default_authenticator(**auth_args)
                    authenticator = ('sqlauth', sqlauth)
                elif self.auth_backend == "ming":
                    from tg.configuration.mongo.auth import create_default_authenticator
                    auth_args, mingauth = create_default_authenticator(**auth_args)
                    authenticator = ('mingauth', mingauth)
                else:
                    authenticator = None

                if authenticator is not None:
                    if pos is None:
                        auth_args['authenticators'] = [authenticator]
                    else:
                        # We make a copy so that we don't modify the original one.
                        auth_args['authenticators'] = copy(auth_args['authenticators'])
                        auth_args['authenticators'][pos] = authenticator

            from tg.configuration.auth import setup_auth
            app = setup_auth(app, skip_authentication=skip_authentication, **auth_args)

        return app

    def add_core_middleware(self, app):
        """Add support for routes dispatch, sessions, and caching.
        This is where you would want to override if you wanted to provide your
        own routing, session, or caching middleware.  Your app_cfg.py might look something
        like this::

            from tg.configuration import AppConfig
            from routes.middleware import RoutesMiddleware
            from beaker.middleware import CacheMiddleware
            from mysessionier.middleware import SessionMiddleware

            class MyAppConfig(AppConfig):
                def add_core_middleware(self, app):
                    app = RoutesMiddleware(app, config['routes.map'])
                    app = SessionMiddleware(app, config)
                    app = CacheMiddleware(app, config)
                    return app
            base_config = MyAppConfig()
        """
        if self.enable_routes:
            warnings.warn("Internal routes support will be deprecated soon, please "
                          "consider using tgext.routes instead", DeprecationWarning)
            from routes.middleware import RoutesMiddleware
            app = RoutesMiddleware(app, config['routes.map'])

        if self.use_sessions:
            app = SessionMiddleware(app, config)
        
        app = CacheMiddleware(app, config)

        return app

    def add_tosca_middleware(self, app):
        """Configure the ToscaWidgets middleware.

        If you would like to override the way the TW middleware works, you might do something like::

            from tg.configuration import AppConfig
            from tw.api import make_middleware as tw_middleware

            class MyAppConfig(AppConfig):

                def add_tosca2_middleware(self, app):

                    app = tw_middleware(app, {
                        'toscawidgets.framework.default_view': self.default_renderer,
                        'toscawidgets.framework.translator': ugettext,
                        'toscawidgets.middleware.inject_resources': False,
                        })
                    return app

            base_config = MyAppConfig()



        The above example would disable resource injection.

        There is more information about the settings you can change
        in the ToscaWidgets `middleware. <http://toscawidgets.org/documentation/ToscaWidgets/modules/middleware.html>`


        """

        import tw
        from tw.api import make_middleware as tw_middleware

        twconfig = {'toscawidgets.framework.default_view': self.default_renderer,
                    'toscawidgets.framework.translator': ugettext,
                    'toscawidgets.middleware.inject_resources': True,
                    }
        for k,v in config.items():
            if k.startswith('toscawidgets.framework.') or k.startswith('toscawidgets.middleware.'):
                twconfig[k] = v

        if 'toscawidgets.framework.resource_variant' in config:
            import tw.api
            tw.api.resources.registry.ACTIVE_VARIANT = config['toscawidgets.framework.resource_variant']
            #remove it from the middleware madness
            del twconfig['toscawidgets.framework.resource_variant']

        app = tw_middleware(app, twconfig)

        if self.default_renderer in ('genshi','mako'):
            tw.framework.default_view = self.default_renderer

        return app

    def add_tosca2_middleware(self, app):
        """Configure the ToscaWidgets2 middleware.

        If you would like to override the way the TW2 middleware works,
        you might do change your app_cfg.py to add something like::

            from tg.configuration import AppConfig
            from tw2.core.middleware import TwMiddleware

            class MyAppConfig(AppConfig):

                def add_tosca2_middleware(self, app):

                    app = TwMiddleware(app,
                        default_engine=self.default_renderer,
                        translator=ugettext,
                        auto_reload_templates = False
                        )

                    return app
            base_config = MyAppConfig()



        The above example would always set the template auto reloading off. (This is normally an
        option that is set within your application's ini file.)
        """
        from tw2.core.middleware import Config, TwMiddleware

        shared_engines = list(set(self.renderers) & set(Config.preferred_rendering_engines))
        if not shared_engines:
            raise TGConfigError('None of the configured rendering engines is supported'
                                'by ToscaWidgets2, unable to configure ToscaWidgets.')

        if self.default_renderer in shared_engines:
            tw2_engines = [self.default_renderer] + shared_engines
            tw2_default_engine = self.default_renderer
        else:
            # If preferred rendering engine is not available in TW2, fallback to another one
            # This happens for Kajiki which is not supported by recent TW2 versions.
            tw2_engines = shared_engines
            tw2_default_engine = shared_engines[0]

        default_tw2_config = dict( default_engine=tw2_default_engine,
                                   preferred_rendering_engines=tw2_engines,
                                   translator=ugettext,
                                   get_lang=lambda: get_lang(all=False),
                                   auto_reload_templates=self.auto_reload_templates,
                                   controller_prefix='/tw2/controllers/',
                                   res_prefix='/tw2/resources/',
                                   debug=config['debug'],
                                   rendering_extension_lookup={
                                        'mako': ['mak', 'mako'],
                                        'genshi': ['genshi', 'html'],
                                        'jinja':['jinja', 'jinja2'],
                                        'kajiki':['kajiki', 'xml']
                                   })
        default_tw2_config.update(self.custom_tw2_config)
        app = TwMiddleware(app, **default_tw2_config)
        return app

    def add_static_file_middleware(self, app):
        app = StaticsMiddleware(app, config['paths']['static_files'])
        return app

    def add_tm_middleware(self, app):
        """Set up the transaction management middleware.

        To abort a transaction inside a TG2 app::

          import transaction
          transaction.doom()

        By default http error responses also roll back transactions, but this
        behavior can be overridden by overriding base_config.commit_veto.

        """
        from tg.support.transaction_manager import TGTransactionManager

        #TODO: remove self.commit_veto option in future release
        #backward compatibility with "commit_veto" option
        config['tm.commit_veto'] = self.commit_veto

        return TGTransactionManager(app, config)

    def add_ming_middleware(self, app):
        """Set up the ming middleware for the unit of work"""
        import ming.odm.middleware
        return ming.odm.middleware.MingMiddleware(app)

    def add_sqlalchemy_middleware(self, app):
        """Set up middleware that cleans up the sqlalchemy session.

        The default behavior of TG 2 is to clean up the session on every
        request.  Only override this method if you know what you are doing!

        """
        return DBSessionRemoverMiddleware(self.DBSession, app)

    def setup_tg_wsgi_app(self, load_environment=None):
        """Create a base TG app, with all the standard middleware.

        ``load_environment``
            A required callable, which sets up the basic evironment
            needed for the application.
        ``setup_vars``
            A dictionary with all special values necessary for setting up
            the base wsgi app.

        """

        def make_base_app(global_conf=None, wrap_app=None, full_stack=False, **app_conf):
            """Create a tg WSGI application and return it.

            ``wrap_app``
                a WSGI middleware component which takes the core turbogears
                application and wraps it -- inside all the WSGI-components
                provided by TG and Pylons. This allows you to work with the
                full environment that your TG application would get before
                anything happens in the application itself.

            ``global_conf``
                The inherited configuration for this application. Normally
                from the [DEFAULT] section of the Paste ini file.

            ``full_stack``
                Whether or not this application provides a full WSGI stack (by
                default, meaning it handles its own exceptions and errors).
                Disable full_stack when this application is "managed" by
                another WSGI middleware.

            ``app_conf``
                The application's local configuration. Normally specified in
                the [app:<name>] section of the Paste ini file (where <name>
                defaults to main).

            """
            from tg import TGApp

            if global_conf is None:
                global_conf = {}

            # Configure the Application environment
            if load_environment:
                load_environment(global_conf, app_conf)

            # trigger the environment_loaded milestone again, so that
            # when load_environment is not provided the attached actions gets performed anyway.
            milestones.environment_loaded.reach()

            # Apply controller wrappers to controller caller
            self._setup_controller_wrappers()

            # TODO: This should be moved in configuration phase.
            # It is here as it requires both the .ini file and AppConfig to be ready
            avoid_sess_touch = config.get('beaker.session.tg_avoid_touch', 'false')
            config['beaker.session.tg_avoid_touch'] = asbool(avoid_sess_touch)

            app = TGApp()
            if wrap_app:
                app = wrap_app(app)

            app = tg.hooks.notify_with_value('before_config', app, context_config=config)

            app = self.add_core_middleware(app)

            if self.auth_backend:
                # Skipping authentication if explicitly requested. Used by
                # repoze.who-testutil:
                skip_authentication = app_conf.get('skip_authentication', False)
                app = self.add_auth_middleware(app, skip_authentication)

            if self.use_transaction_manager:
                app = self.add_tm_middleware(app)

            # TODO: Middlewares before this point should be converted to App Wrappers.
            # They provide some basic TG features like AUTH, Caching and transactions
            # which should be app wrappers to make possible to add wrappers in the
            # stack before or after them.

            if self.use_toscawidgets:
                app = self.add_tosca_middleware(app)

            if self.use_toscawidgets2:
                app = self.add_tosca2_middleware(app)

            # from here on the response is a generator
            # so any middleware that relies on the response to be
            # a string needs to be applied before this point.

            if self.use_sqlalchemy:
                app = self.add_sqlalchemy_middleware(app)

            if self.use_ming:
                app = self.add_ming_middleware(app)

            if config.get('make_body_seekable'):
                app = SeekableRequestBodyMiddleware(app)

            if 'PYTHONOPTIMIZE' in os.environ:
                warnings.warn("Forcing full_stack=False due to PYTHONOPTIMIZE enabled. "+\
                              "Error Middleware will be disabled", RuntimeWarning, stacklevel=2)
                full_stack = False

            if asbool(full_stack):
                if (self.auth_backend is None
                        and 401 not in self.handle_status_codes):
                    # If there's no auth backend configured which traps 401
                    # responses we redirect those responses to a nicely
                    # formatted error page
                    self.handle_status_codes.append(401)
                # This should never be true for internal nested apps
                app = self.add_error_middleware(global_conf, app)

            # Establish the registry for this application
            app = RegistryManager(app, streaming=config.get('registry_streaming', True),
                                  preserve_exceptions=asbool(global_conf.get('debug')))

            # Place the debuggers after the registry so that we
            # can preserve context in case of exceptions
            app = self.add_debugger_middleware(global_conf, app)

            # Static files (if running in production, and Apache or another
            # web server is serving static files)

            #if the user has set the value in app_config, don't pull it from the ini
            forced_serve_static = config.get('serve_static')
            if forced_serve_static is not None:
                self.serve_static = asbool(forced_serve_static)

            if self.serve_static:
                app = self.add_static_file_middleware(app)

            app = tg.hooks.notify_with_value('after_config', app, context_config=config)

            return app

        return make_base_app

    def make_wsgi_app(self, **app_conf):
        loadenv = self.make_load_environment()
        return self.setup_tg_wsgi_app(loadenv)(**app_conf)
