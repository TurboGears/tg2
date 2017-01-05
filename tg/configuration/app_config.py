"""Configuration Helpers for TurboGears 2"""
import os
import logging
import warnings
from copy import copy, deepcopy
import mimetypes
from collections import MutableMapping as DictMixin, deque
from tg._compat import import_module
from tg.appwrappers.identity import IdentityApplicationWrapper

from tg.support.middlewares import StaticsMiddleware, SeekableRequestBodyMiddleware, \
    DBSessionRemoverMiddleware
from tg.support.registry import RegistryManager
from tg.support.converters import asbool, asint, aslist
from tg.request_local import config as reqlocal_config

import tg
from tg.util import Bunch, DottedFileNameFinder
from tg.configuration import milestones
from tg.configuration.utils import TGConfigError, coerce_config, get_partial_dict, coerce_options, \
    DependenciesList
from tg.renderers.genshi import GenshiRenderer
from tg.renderers.json import JSONRenderer
from tg.renderers.jinja import JinjaRenderer
from tg.renderers.mako import MakoRenderer
from tg.renderers.kajiki import KajikiRenderer

from tg.appwrappers.i18n import I18NApplicationWrapper
from tg.appwrappers.caching import CacheApplicationWrapper
from tg.appwrappers.session import SessionApplicationWrapper
from tg.appwrappers.errorpage import ErrorPageApplicationWrapper
from tg.appwrappers.transaction_manager import TransactionApplicationWrapper
from tg.appwrappers.mingflush import MingApplicationWrapper

log = logging.getLogger(__name__)


class DispatchingConfigWrapper(DictMixin):
    """Wrapper for the Dispatching configuration.

    Simple wrapper for the DispatchingConfig object that provides attribute
    style access to the config dictionary.

    This class works by proxying all attribute and dictionary access to
    the underlying DispatchingConfig config object, which is an application local
    proxy that allows for multiple TG2 applications to live
    in the same process simultaneously, but to always get the right
    config data for the application that's requesting them.

    """

    def __init__(self, dict_to_wrap):
        """Initialize the object by passing in config to be wrapped"""
        self.__dict__['config_proxy'] = dict_to_wrap

    def __getitem__(self, key):
        return self.config_proxy.current_conf()[key]

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
                return get_partial_dict(key, self.config_proxy.current_conf(), Bunch)

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
    'i18n.lang': None
}

# Push an empty config so all accesses to config at import time have something
# to look at and modify. This config will be merged with the app's when it's
# built in the paste.app_factory entry point.
reqlocal_config.push_process_config(deepcopy(defaults))

#Create a config object that has attribute style lookup built in.
config = DispatchingConfigWrapper(reqlocal_config)


def call_controller(tg_config, controller, remainder, params):
    return controller(*remainder, **params)


class _DeprecatedControllerWrapper(object):
    def __init__(self, controller_wrapper, config, next_wrapper):
        # Backward compatible old-way of configuring controller wrappers
        warnings.warn("Controller wrapper will now accept the configuration"
                      "as parameter when called instead of receiving it as"
                      "a constructor parameter, please refer to the documentation"
                      "to update your controller wrappers",
                      DeprecationWarning, stacklevel=3)

        def _adapted_next_wrapper(controller, remainder, params):
            return next_wrapper(tg.config._current_obj(),
                                controller, remainder, params)

        self.wrapper = controller_wrapper(config, _adapted_next_wrapper)

    def __call__(self, config, controller, remainder, params):
        return self.wrapper(controller, remainder, params)


class AppConfig(Bunch):
    """Class to store application configuration.

    This class should have configuration/setup information
    that is *necessary* for proper application function.
    Deployment specific configuration information should go in
    the config files (e.g. development.ini or deployment.ini).

    AppConfig instances have a number of methods that are meant to be
    overridden by users who wish to have finer grained control over
    the setup of the WSGI environment in which their application is run.

    This is the place to configure your application, database,
    transaction handling, error handling, etc.

    Configuration Options provided:

        - ``debug`` -> Enables / Disables debug mode. **Can be set from .ini file**
        - ``serve_static`` -> Enable / Disable serving static files. **Can be set from .ini file**
        - ``use_dotted_templatenames`` -> Use template names as packages in @expose instead of file paths.
          This is usually the default unless TG is started in Minimal Mode. **Can be set from .ini file**
        - ``registry_streaming`` -> Enable streaming of responses, this is enabled by default.
          **Can be set from .ini file**
        - ``paths`` -> Dictionary of directories where templates, static files and controllers are found::

            {
                'controllers': 'my/path/to/controlllers',
                'static_files': 'my/path/to/files',
                'templates': ['list/of/paths/to/templates']
            )
        - ``use_toscawidgets`` -> Enable ToscaWidgets1, this is deprecated.
        - ``use_toscawidgets2`` -> Enable ToscaWidgets2
        - ``prefer_toscawidgets2`` -> When both TW2 and TW1 are enabled prefer TW2. **Can be set from .ini file**
        - ``custom_tw2_config`` -> Dictionary of configuration options for TW2, refer to
          :class:`.tw2.core.middleware.Config` for available options.
        - ``auth_backend`` -> Authentication Backend, can be ``None``, ``sqlalchemy`` or ``ming``.
        - ``sa_auth`` -> Simple Authentication configuration dictionary.
          This is a Dictionary that contains the configuration options for ``repoze.who``,
          see :ref:`authentication` for available options. Basic options include:

            - ``cookie_secret`` -> Secret phrase used to verify auth cookies.
            - ``authmetadata`` -> Authentication and User Metadata Provider for TurboGears
            - ``post_login_url`` -> Redirect users here after login
            - ``post_logout_url`` -> Redirect users here when they logout
        - ``package`` -> Application Package, this is used to configure paths as being inside a python
        - ``app_globals`` -> Application Globals class, by default build from ``package.lib.app_globals``.
          package. Which enables serving templates, controllers, app globals and so on from the package itself.
        - ``helpers`` -> Template Helpers, by default ``package.lib.helpers`` is used.
        - ``model`` -> The models module (or object) where all the models, DBSession and init_models method are
           available. By default ``package.model`` is used.
        - ``renderers`` -> List of enabled renderers names.
        - ``default_renderer`` -> When not specified, use this renderer for templates.
        - ``auto_reload_templates`` -> Automatically reload templates when modified (disable this on production
          for a performance gain). **Can be set from .ini file**
        - ``use_ming`` -> Enable/Disable Ming as Models storage.
        - ``ming.url`` -> Url of the MongoDB database
        - ``ming.db`` -> If Database is not provided in ``ming.url`` it can be specified here.
        - ``ming.connection.*`` -> Options to configure the ming connection,
          refer to :func:`ming.datastore.create_datastore` for available options.
        - ``use_sqlalchemy`` -> Enable/Disable SQLalchemy as Models storage.
        - ``sqlalchemy.url`` -> Url of the SQLAlchemy database. Refer to :ref:`sqla_master_slave` for
          configuring master-slave urls.
    """
    CONFIG_OPTIONS = {
        'debug': asbool,
        'serve_static': asbool,
        'auto_reload_templates': asbool,
        'use_dotted_templatenames': asbool,
        'registry_streaming': asbool,
        'use_toscawidgets2': asbool,
        'prefer_toscawidgets2': asbool
    }

    def __init__(self, minimal=False, root_controller=None):
        """Creates some configuration defaults"""

        # Create a few bunches we know we'll use
        self.paths = Bunch()

        # Provide a default app_globals for single file applications
        self.app_globals = None
        self.helpers = None

        # And also very often...
        self.sa_auth = Bunch()

        # Set individual defaults
        self.auto_reload_templates = True
        self.auth_backend = None
        self.serve_static = not minimal

        self.renderers = []
        self.default_renderer = 'genshi'
        self.render_functions = Bunch()
        self.rendering_engines = {}
        self.rendering_engines_without_vars = set()
        self.rendering_engines_options = {}

        self.enable_routing_args = False
        self.disable_request_extensions = minimal

        self.use_ming = False
        self.use_sqlalchemy = False

        self['tm.enabled'] = not minimal

        self.use_toscawidgets = not minimal
        self.use_toscawidgets2 = False
        self.prefer_toscawidgets2 = False
        self.use_dotted_templatenames = not minimal
        self.registry_streaming = True

        self['session.enabled'] = not minimal
        self['cache.enabled'] = not minimal
        self['i18n.enabled'] = not minimal

        # Support Custom Error pages
        self.status_code_redirect = False  # Use old StatusCodeRedirect middleware
        self['errorpage.enabled'] = not minimal
        self['errorpage.status_codes'] = [403, 404]

        # Registry for functions to be called on startup/teardown
        self.call_on_startup = []
        self.call_on_shutdown = []
        self.controller_caller = call_controller
        self.controller_wrappers = []
        self.application_wrappers = DependenciesList()

        # override this variable to customize how the tw2 middleware is set up
        self.custom_tw2_config = {}

        # This is for minimal mode to set root controller manually
        if root_controller is not None:
            self['tg.root_controller'] = root_controller

        self.register_rendering_engine(JSONRenderer)
        self.register_rendering_engine(GenshiRenderer)
        self.register_rendering_engine(MakoRenderer)
        self.register_rendering_engine(JinjaRenderer)
        self.register_rendering_engine(KajikiRenderer)

        self.register_wrapper(I18NApplicationWrapper, after=True)
        self.register_wrapper(IdentityApplicationWrapper, after=True)
        self.register_wrapper(SessionApplicationWrapper, after=True)
        self.register_wrapper(CacheApplicationWrapper, after=True)
        self.register_wrapper(MingApplicationWrapper, after=True)
        self.register_wrapper(TransactionApplicationWrapper, after=True)
        self.register_wrapper(ErrorPageApplicationWrapper, after=True)

    def _get_root_module(self):
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
                      "AppConfig.register_controller_wrapper instead", DeprecationWarning)

        if hook_name == 'controller_wrapper':
            tg.hooks.wrap_controller(func)
        else:
            tg.hooks.register(hook_name, func)

    def register_controller_wrapper(self, wrapper, controller=None):
        """Registers a TurboGears controller wrapper.

        Controller Wrappers are much like a **decorator** applied to
        every controller.
        They receive :class:`tg.configuration.AppConfig` instance
        as an argument and the next handler in chain and are expected
        to return a new handler that performs whatever it requires
        and then calls the next handler.

        A simple example for a controller wrapper is a simple logging wrapper::

            def controller_wrapper(app_config, caller):
                def call(*args, **kw):
                    try:
                        print 'Before handler!'
                        return caller(*args, **kw)
                    finally:
                        print 'After Handler!'
                return call

            base_config.register_controller_wrapper(controller_wrapper)

        It is also possible to register wrappers for a specific controller::

            base_config.register_controller_wrapper(controller_wrapper, controller=RootController.index)
        """
        if milestones.environment_loaded.reached:
            log.warning('Controller Wrapper %s registered after environment loaded'
                        'milestone has been reached, the wrapper will be used only'
                        'for future TGApp instances.', wrapper)

        log.debug("Registering %s controller wrapper for controller: %s",
                  wrapper, controller or 'ALL')

        if controller is None:
            self.controller_wrappers.append(wrapper)
        else:
            from tg.decorators import Decoration
            deco = Decoration.get_decoration(controller)
            deco._register_controller_wrapper(wrapper)

    def register_wrapper(self, wrapper, after=None):
        """Registers a TurboGears application wrapper.

        Application wrappers are like WSGI middlewares but
        are executed in the context of TurboGears and work
        with abstractions like Request and Respone objects.

        See :class:`tg.appwrappers.base.ApplicationWrapper` for
        complete definition of application wrappers.

        The ``after`` parameter defines their position into the
        wrappers chain. The default value ``None`` means they are
        executed in a middle point, so they run after the TurboGears
        wrappers like :class:`.ErrorPageApplicationWrapper` which
        can intercept their response and return an error page.

        Builtin TurboGears wrappers are usually registered with
        ``after=True`` which means they run furthest away from the
        application itself and can intercept the response of any
        other wrapper.

        Providing ``after=False`` means the wrapper will be registered
        near to the application itself (so wrappers registered at default
        position and with after=True will be able to see its response).

        ``after`` parameter can also accept an *application wrapper class*.
        In such case the registered wrapper will be registered right after
        the specified wrapper and so will be a little further from the
        application then the specified one (can see the response of the
        specified one).

        """
        if milestones.environment_loaded.reached:
            # Wrappers are consumed by TGApp constructor, and all the hooks available
            # after the milestone and that could register new wrappers are actually
            # called after TGApp constructors and so the wrappers wouldn't be applied.
            log.warning('Application Wrapper %s registered after environment loaded'
                        'milestone has been reached, the wrapper will be used only'
                        'for future TGApp instances.', wrapper)

        self.application_wrappers.add(wrapper, after=after)

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

        self._configure_package_paths()
        self._configure_renderers()
        self._configure_error_pages()
        self._configure_ming()
        self._configure_transaction_manager()
        self._configure_mimetypes()

        if self.prefer_toscawidgets2:
            self.use_toscawidgets = False
            self.use_toscawidgets2 = True

        conf = deepcopy(defaults)
        conf.update(self)
        conf.update(deepcopy(global_conf))
        conf.update(app_conf)
        conf.update(dict(app_conf=app_conf, global_conf=global_conf))

        # Coerce some options that are bool
        conf.update(coerce_options(
            conf,
            self.CONFIG_OPTIONS
        ))

        # Load the errorware configuration from the Paste configuration file
        # These all have defaults, and emails are only sent if configured and
        # if this application is running in production mode
        errorware = {}
        errorware['debug'] = conf['debug']
        if not errorware['debug']:
            errorware['debug'] = False

            trace_errors_config = coerce_config(conf, 'trace_errors.', {'enable': asbool,
                                                                        'smtp_use_tls': asbool,
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

        slowreqsware = coerce_config(conf, 'trace_slowreqs.', {'smtp_use_tls': asbool,
                                                               'dump_request_size': asint,
                                                               'dump_request': asbool,
                                                               'dump_local_frames': asbool,
                                                               'dump_local_frames_count': asint,
                                                               'enable': asbool,
                                                               'interval': asint,
                                                               'exclude': aslist})
        slowreqsware.setdefault('error_subject_prefix', 'Slow Request: ')
        slowreqsware.setdefault('error_message', 'A request is taking too much time')
        for erroropt in errorware:
            slowreqsware.setdefault(erroropt, errorware[erroropt])
        conf['tg.slowreqs'] = slowreqsware

        # Copy in some defaults
        if 'cache_dir' in conf:
            conf.setdefault('session.data_dir', os.path.join(conf['cache_dir'], 'sessions'))
            conf.setdefault('cache.data_dir', os.path.join(conf['cache_dir'], 'cache'))
        conf['tg.cache_dir'] = conf.pop('cache_dir', conf['app_conf'].get('cache_dir'))

        if not conf['paths']['static_files']:
            conf['serve_static'] = False

        conf['application_root_module'] = self._get_root_module()
        if conf['paths']['root']:
            conf['localedir'] = os.path.join(conf['paths']['root'], 'i18n')
        else:
            conf['i18n.enabled'] = False

        # Load conf dict into the global config object
        try:
            reqlocal_config.pop_process_config()
        except IndexError:  # pragma: no cover
            log.warn('No global config in place, at least defaults should have been here')
        finally:
            reqlocal_config.push_process_config(conf)

        self.after_init_config(conf)

        milestones.config_ready.reach()
        return conf

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

    def _configure_ming(self):
        try:
            autoflush_enabled = self['ming.autoflush']
        except KeyError:
            autoflush_enabled = True

        self['ming.autoflush'] = self.use_ming and autoflush_enabled

    def _configure_error_pages(self):
        if (self.auth_backend is None and 401 not in self['errorpage.status_codes']):
            # If there's no auth backend configured which traps 401
            # responses we redirect those responses to a nicely
            # formatted error page
            self['errorpage.status_codes'] = list(self['errorpage.status_codes']) + [401]

        if self.status_code_redirect is True:
            # The codes TG should display an error page for. All other HTTP errors are
            # sent to the client or left for some middleware above us to handle
            self.handle_error_page = self['errorpage.enabled']
            self.handle_status_codes = self['errorpage.status_codes']
            self['errorpage.enabled'] = False

    def _configure_transaction_manager(self):
        if getattr(self, 'use_transaction_manager', False):
            warnings.warn("Transaction Manager middleware has been deprecated, "
                          "please use the tm.enabled=True option to switch "
                          "to the transaction application wrapper",
                          DeprecationWarning, stacklevel=2)
            self['tm.enabled'] = False

            if not self.use_sqlalchemy:
                log.debug('Disabling Transaction Manager as SQLAlchemy is not available')
                self.use_transaction_manager = False

    def _configure_package_paths(self):
        try:
            self.package
        except AttributeError:
            # if we don't have a specified package, don't try
            # helpers from the package expect the user to specify them.
            paths = Bunch()
        else:
            root = os.path.dirname(os.path.abspath(self.package.__file__))
            paths = Bunch(
                root=root,
                controllers=os.path.join(root, 'controllers'),
                static_files=os.path.join(root, 'public'),
                templates=[os.path.join(root, 'templates')]
            )

        # If the user defined custom paths, then use them instead of the
        # default ones:
        paths.update(self.paths)

        # Ensure all paths are set, load default ones otherwise
        for key, val in defaults['paths'].items():
            paths.setdefault(key, val)

        self.paths = paths

    def after_init_config(self, conf):
        """
        Override this method to set up configuration variables at the application
        level.  This method will be called after your configuration object has
        been initialized on startup.  Here is how you would use it to override
        the default setting of tg.strict_tmpl_context ::

            from tg.configuration import AppConfig

            class MyAppConfig(AppConfig):
                def after_init_config(self, conf):
                    conf['tg.strict_tmpl_context'] = False

            base_config = MyAppConfig()

        """

    def _setup_helpers_and_globals(self, conf):
        """Add helpers and globals objects to the ``conf``.

        Override this method to customize the way that ``app_globals`` and ``helpers``
        are setup. TurboGears expects them to be available in ``conf`` dictionary
        as ``tg.app_globals`` and ``helpers``.
        """
        # Setup AppGlobals
        gclass = conf.pop('app_globals', None)
        if gclass is None:
            try:
                gclass = conf['package'].lib.app_globals.Globals
            except AttributeError:
                pass

        if gclass is None:
            try:
                app_globals_mod = import_module('.lib.app_globals', package=self.package.__name__)
                gclass = getattr(app_globals_mod, 'Globals')
            except (ImportError, AttributeError):
                pass

        if gclass is None:
            log.warn('app_globals not provided and lib.app_globals.Globals is not available.')
            gclass = Bunch

        g = gclass()

        g.dotted_filename_finder = DottedFileNameFinder()
        conf['tg.app_globals'] = g

        if conf.get('tg.pylons_compatible', True):
            conf['pylons.app_globals'] = g

        # Setup Helpers
        h = conf.get('helpers', None)
        if h is None:
            try:
                h = conf['package'].lib.helpers
            except AttributeError:
                pass

        if h is None:
            try:
                h = import_module('.lib.helpers', package=self.package.__name__)
            except (ImportError, AttributeError):
                pass

        if h is None:
            log.warn('helpers not provided and lib.helpers is not available.')
            h = Bunch()

        conf['helpers'] = h

    def _setup_persistence(self, conf):
        """Configures application persistence model"""
        if conf['use_sqlalchemy']:
            self._setup_sqlalchemy(conf)
        if conf['use_ming']:
            self._setup_ming(conf)

    def _setup_ming(self, conf):
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

        datastore_options = coerce_config(conf, 'ming.connection.', {'max_pool_size':asint,
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

        datastore = create_ming_datastore(conf['ming.url'],
                                          conf.get('ming.db', ''),
                                          **datastore_options)
        conf['tg.app_globals'].ming_datastore = datastore

        try:
            package_models = conf['package'].model
        except AttributeError:
            package_models = None

        model = conf.get('model', package_models)
        if model is None:
            raise TGConfigError('Ming enabled, but no models provided')

        ming_session = model.init_model(datastore)
        if ming_session is not None:
            # If init_model returns a specific session, keep it around
            # as the MongoDB Session.
            conf['MingSession'] = ming_session

        if 'DBSession' not in conf:
            # If the user hasn't specified a default session, assume
            # he/she uses the default DBSession in model
            conf['DBSession'] = model.DBSession

    def _setup_sqlalchemy(self, conf):
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

        balanced_master = conf.get('sqlalchemy.master.url')
        if not balanced_master:
            engine = engine_from_config(conf, 'sqlalchemy.')
        else:
            engine = engine_from_config(conf, 'sqlalchemy.master.')
            conf['balanced_engines'] = {'master':engine,
                                        'slaves':{},
                                        'all':{'master':engine}}

            all_engines = conf['balanced_engines']['all']
            slaves = conf['balanced_engines']['slaves']
            for entry in conf.keys():
                if entry.startswith('sqlalchemy.slaves.'):
                    slave_path = entry.split('.')
                    slave_name = slave_path[2]
                    if slave_name == 'master':
                        raise TGConfigError('A slave node cannot be named master')
                    slave_config = '.'.join(slave_path[:3])
                    all_engines[slave_name] = slaves[slave_name] = engine_from_config(conf, slave_config+'.')

            if not conf['balanced_engines']['slaves']:
                raise TGConfigError('When running in balanced mode your must specify at least a slave node')

        # Pass the engine to initmodel, to be able to introspect tables
        conf['tg.app_globals'].sa_engine = engine

        try:
            package_models = conf['package'].model
        except AttributeError:
            package_models = None

        model = conf.get('model', package_models)
        if model is None:
            raise TGConfigError('SQLAlchemy enabled, but no models provided')

        sqla_session = model.init_model(engine)
        if sqla_session is not None:
            # If init_model returns a specific session, keep it around
            # as the SQLAlchemy Session.
            conf['SQLASession'] = sqla_session

        if 'DBSession' not in conf:
            # If the user hasn't specified a default session, assume
            # he/she uses the default DBSession in model
            conf['DBSession'] = model.DBSession

    def _setup_auth(self, conf):
        """
        Override this method to define how you would like the authentication options
        to be setup for your application.
        """
        if hasattr(self, 'setup_sa_auth_backend'):
            warnings.warn("setup_sa_auth_backend is deprecated, please override"
                          "AppConfig._setup_auth instead", DeprecationWarning)
            return self.setup_sa_auth_backend()

        if conf['auth_backend'] in ("ming", "sqlalchemy"):
            sa_auth_conf = conf['sa_auth']
            if 'cookie_secret' not in sa_auth_conf and 'session.secret' not in conf:
                raise TGConfigError("You must provide a value for authentication cookies secret. "
                                    "Make sure that you have one of those options in app_cfg.py: "
                                    "'sa_auth.cookie_secret' or 'session.secret'")

            # The developer must have defined a 'sa_auth' section, because
            # values such as the User, Group or Permission classes must be
            # explicitly defined.
            sa_auth_conf.setdefault('form_plugin', None)
            sa_auth_conf.setdefault(
                'cookie_secret',
                conf.get('session.secret', conf.get('beaker.session.secret'))
            )

    def _setup_controller_wrappers(self, conf):
        # This trashes away the current config['controller_caller']
        # so that the call is idempotent.
        base_controller_caller = call_controller

        controller_caller = base_controller_caller
        for wrapper in conf.get('controller_wrappers', []):
            try:
                controller_caller = wrapper(controller_caller)
            except TypeError:
                controller_caller = _DeprecatedControllerWrapper(wrapper, conf, controller_caller)

        conf['controller_caller'] = controller_caller

    def _setup_renderers(self, conf):
        renderers = conf['renderers']
        rendering_engines = conf['rendering_engines']

        for renderer in renderers[:]:
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
                    renderers.remove(renderer)
            elif renderer in rendering_engines:
                rendering_engine = rendering_engines[renderer]
                engines = rendering_engine.create(conf, conf['tg.app_globals'])
                if engines is None:
                    log.error('Failed to initialize %s template engine, removing it...' % renderer)
                    renderers.remove(renderer)
                else:
                    conf['render_functions'].update(engines)
            else:
                raise TGConfigError('This configuration object does '
                                    'not support the %s renderer' % renderer)

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

            app_config = self._init_config(global_conf, app_conf)
            tg.hooks.notify('initialized_config', args=(self, app_config))
            tg.hooks.notify('startup', trap_exceptions=True)

            self._setup_helpers_and_globals(app_config)
            self._setup_auth(app_config)
            self._setup_renderers(app_config)
            self._setup_persistence(app_config)

            # Trigger milestone here so that it gets triggered even when
            # websetup (setup-app command) is performed.
            milestones.environment_loaded.reach()

            return app_config

        return load_environment

    def _add_error_middleware(self, app_config, app):
        """Add middleware which handles errors and exceptions."""
        from tg.error import ErrorReporter
        app = ErrorReporter(app, app_config, **app_config['tg.errorware'])

        if app_config['status_code_redirect'] is True:
            warnings.warn("Support for StatusCodeRedirect is deprecated and "
                          "will be removed in next major release", DeprecationWarning)

            if app_config['handle_error_page']:
                from tg.support.middlewares import StatusCodeRedirect
                # Display error documents for self.handle_status_codes status codes (and
                # 500 when debug is disabled)
                handled_status_codes = app_config['handle_status_codes']
                if not asbool(app_config['debug']):
                    handled_status_codes += [500]
                app = StatusCodeRedirect(app, handled_status_codes)

        return app

    def _add_slowreqs_middleware(self, app_config, app):
        from tg.error import SlowReqsReporter
        return SlowReqsReporter(app, app_config, **app_config['tg.slowreqs'])

    def _add_debugger_middleware(self, app_config, app):
        from tg.error import ErrorHandler
        return ErrorHandler(app, app_config)

    def _add_auth_middleware(self, app_config, app):
        """
        Configure authentication and authorization.
        """
        # Start with the current configured authentication options.
        # Depending on the auth backend a new auth_args dictionary
        # can replace this one later on.
        skip_authentication = asbool(app_config.get('skip_authentication', False))
        auth_args = copy(app_config['sa_auth'])

        # Configuring auth logging:
        if 'log_stream' not in auth_args:
            auth_args['log_stream'] = logging.getLogger('auth')

        # Removing keywords not used by repoze.who:
        auth_args.pop('password_encryption_method', None)

        if not skip_authentication and 'cookie_secret' not in auth_args:
            raise TGConfigError("base_config.sa_auth.cookie_secret is required "
                                "you must define it in app_cfg.py or set "
                                "sa_auth.cookie_secret in development.ini")

        if 'authmetadata' not in auth_args:  # pragma: no cover
            warnings.warn("Authentication configured without authmetadata, "
                          "this is not supported anymore and will be removed in future versions",
                          DeprecationWarning)

            # authmetadata not provided, fallback to old authentication setup
            if self.auth_backend == "sqlalchemy":
                from repoze.what.plugins.quickstart import setup_sql_auth
                app = setup_sql_auth(app, skip_authentication=skip_authentication, **auth_args)
            elif self.auth_backend == "ming":
                from tgming import setup_ming_auth
                app = setup_ming_auth(app, skip_authentication=skip_authentication, **auth_args)
        else:
            # Removing authmetadata as is not used by repoze.who:
            tgauthmetadata = auth_args.pop('authmetadata', None)

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
                if getattr(tgauthmetadata, 'authenticate', None) is not None:
                    from tg.configuration.auth import create_default_authenticator
                    auth_args, tgauth = create_default_authenticator(tgauthmetadata, **auth_args)
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

    def _add_core_middleware(self, conf, app):
        """Add support for sessions, and caching middlewares

        Those are all deprecated middlewares and will be removed in future TurboGears
        versions as they have been replaced by other tools.
        """
        if conf.get('use_session_middleware', False):
            warnings.warn('SessionMiddleware is deprecated and will be removed soon, '
                          'please consider using SessionApplicationWrapper instead.',
                          DeprecationWarning)
            from tg.support.middlewares import SessionMiddleware, BeakerSessionMiddleware
            if BeakerSessionMiddleware is object:  # pragma: no cover
                raise ImportError('Beaker not installed')
            app = SessionMiddleware(app, conf)

        if conf.get('use_cache_middleware', False):
            warnings.warn('CacheMiddleware is deprecated and will be removed soon, '
                          'please consider using CacheApplicationWrapper instead.',
                          DeprecationWarning)
            from tg.support.middlewares import CacheMiddleware, BeakerCacheMiddleware
            if BeakerCacheMiddleware is object:  # pragma: no cover
                raise ImportError('Beaker not installed')
            app = CacheMiddleware(app, conf)

        return app

    def _add_tosca_middleware(self, conf, app):
        """Configure the ToscaWidgets middleware"""
        import tw
        from tw.api import make_middleware as tw_middleware
        from tg.i18n import ugettext

        twconfig = {'toscawidgets.framework.default_view': conf['default_renderer'],
                    'toscawidgets.framework.translator': ugettext,
                    'toscawidgets.middleware.inject_resources': True,
                    }
        for k,v in conf.items():
            if k.startswith('toscawidgets.framework.') or k.startswith('toscawidgets.middleware.'):
                twconfig[k] = v

        resource_variant = conf.get('toscawidgets.framework.resource_variant')
        if resource_variant is not None:
            import tw.api
            tw.api.resources.registry.ACTIVE_VARIANT = resource_variant
            # remove it from the middleware madness
            del twconfig['toscawidgets.framework.resource_variant']

        app = tw_middleware(app, twconfig)

        if conf['default_renderer'] in ('genshi','mako'):
            tw.framework.default_view = conf['default_renderer']

        return app

    def _add_tosca2_middleware(self, conf, app):
        """Configure the ToscaWidgets2 middleware"""
        from tw2.core.middleware import Config, TwMiddleware
        from tg.i18n import ugettext, get_lang

        available_renderers = set(conf['renderers'])
        shared_engines = list(available_renderers & set(Config.preferred_rendering_engines))
        if not shared_engines:
            raise TGConfigError('None of the configured rendering engines is supported'
                                'by ToscaWidgets2, unable to configure ToscaWidgets.')

        default_renderer = conf['default_renderer']
        if default_renderer in shared_engines:
            tw2_engines = [default_renderer] + shared_engines
            tw2_default_engine = default_renderer
        else:
            # If preferred rendering engine is not available in TW2, fallback to another one
            tw2_engines = shared_engines
            tw2_default_engine = shared_engines[0]

        default_tw2_config = dict(default_engine=tw2_default_engine,
                                  preferred_rendering_engines=tw2_engines,
                                  translator=ugettext,
                                  get_lang=lambda: get_lang(all=False),
                                  auto_reload_templates=conf['auto_reload_templates'],
                                  controller_prefix='/tw2/controllers/',
                                  res_prefix='/tw2/resources/',
                                  debug=conf['debug'],
                                  rendering_extension_lookup={
                                       'mako': ['mak', 'mako'],
                                       'genshi': ['genshi', 'html'],
                                       'jinja': ['jinja', 'jinja2'],
                                       'kajiki': ['kajiki', 'xhtml', 'xml']
                                  })

        default_tw2_config.update(conf.get('custom_tw2_config', {}))
        app = TwMiddleware(app, **default_tw2_config)
        return app

    def _add_static_file_middleware(self, conf, app):
        app = StaticsMiddleware(app, conf['paths']['static_files'])
        return app

    def _add_tm_middleware(self, conf, app):
        """Set up the transaction management middleware.

        To abort a transaction inside a TG2 app::

          import transaction
          transaction.doom()

        By default http error responses also roll back transactions, but this
        behavior can be overridden by overriding base_config['tm.commit_veto'].

        """
        warnings.warn("transaction manager middleware has been replaced by "
                      "TransactionApplicationWrapper", DeprecationWarning, stacklevel=2)
        from tg.support.transaction_manager import TGTransactionManager

        # TODO: remove self.commit_veto option in future release
        # backward compatibility with "commit_veto" option
        if 'commit_veto' in conf:
            conf['tm.commit_veto'] = conf['commit_veto']
            warnings.warn("commit_veto option has been replaced by tm.commit_veto",
                          DeprecationWarning, stacklevel=2)

        return TGTransactionManager(app, conf)

    def _add_ming_middleware(self, conf, app):
        """Set up the ming middleware for the unit of work"""
        from tg.support.middlewares import MingSessionRemoverMiddleware
        from ming.odm import ThreadLocalODMSession
        return MingSessionRemoverMiddleware(ThreadLocalODMSession, app)

    def _add_sqlalchemy_middleware(self, conf, app):
        """Set up middleware that cleans up the sqlalchemy session.

        The default behavior of TG 2 is to clean up the session on every
        request.  Only override this method if you know what you are doing!

        """
        dbsession = conf.get('SQLASession')
        if dbsession is None:
            dbsession = conf['DBSession']
        return DBSessionRemoverMiddleware(dbsession, app)

    def _add_seekable_body_middleware(self, conf, app):
        """Make the request body seekable, so it can be read multiple times."""
        return SeekableRequestBodyMiddleware(app)

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
                app_config = load_environment(global_conf, app_conf)
            else:
                app_config = tg.config._current_obj()

                # In case load_environment was not performed we manually trigger all
                # the milestones to ensure that events related to configuration milestones
                # are performed in any case.
                milestones.config_ready.reach()
                milestones.renderers_ready.reach()
                milestones.environment_loaded.reach()

            # Apply controller wrappers to controller caller
            self._setup_controller_wrappers(app_config)

            app = TGApp(app_config)

            tg.hooks.notify('configure_new_app', args=(app,))

            if wrap_app:
                app = wrap_app(app)

            app = tg.hooks.notify_with_value('before_config', app)

            app = self._add_core_middleware(app_config, app)

            if app_config.get('auth_backend', False):
                app = self._add_auth_middleware(app_config, app)

            if app_config.get('use_transaction_manager', False):
                app = self._add_tm_middleware(app_config, app)

            # TODO: Middlewares before this point should be converted to App Wrappers.
            # They provide some basic TG features like AUTH, Caching and transactions
            # which should be app wrappers to make possible to add wrappers in the
            # stack before or after them.

            if app_config.get('use_toscawidgets', False):
                app = self._add_tosca_middleware(app_config, app)

            if app_config.get('use_toscawidgets2', False):
                app = self._add_tosca2_middleware(app_config, app)

            # from here on, due to TW2, the response is a generator
            # so any middleware that relies on the response to be
            # a string needs to be applied before this point.

            if app_config.get('use_sqlalchemy', False):
                app = self._add_sqlalchemy_middleware(app_config, app)

            if app_config.get('use_ming', False):
                app = self._add_ming_middleware(app_config, app)

            if app_config.get('make_body_seekable', False):
                app = self._add_seekable_body_middleware(app_config, app)

            if asbool(full_stack):
                # This should never be true for internal nested apps
                app = self._add_slowreqs_middleware(app_config, app)
                app = self._add_error_middleware(app_config, app)

            # Establish the registry for this application
            app = RegistryManager(app, streaming=asbool(app_config.get('registry_streaming', True)),
                                  preserve_exceptions=asbool(app_config.get('debug')))

            # Place the debuggers after the registry so that we
            # can preserve context in case of exceptions
            app = self._add_debugger_middleware(app_config, app)

            # Static files (if running in production, and Apache or another
            # web server is serving static files)
            if app_config.get('serve_static', False):
                app = self._add_static_file_middleware(app_config, app)

            app = tg.hooks.notify_with_value('after_config', app)

            return app

        return make_base_app

    def make_wsgi_app(self, **app_conf):
        loadenv = self.make_load_environment()
        return self.setup_tg_wsgi_app(loadenv)(**app_conf)
