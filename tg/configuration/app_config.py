"""Configuration Helpers for TurboGears 2"""
import os
import logging
import warnings
from copy import copy, deepcopy
from collections import MutableMapping as DictMixin, deque
from tg.appwrappers.identity import IdentityApplicationWrapper

from tg.support.middlewares import StaticsMiddleware, SeekableRequestBodyMiddleware, \
    DBSessionRemoverMiddleware
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
    'tg.app_globals': None,
    'tg.strict_tmpl_context': True,
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


class AppConfig(object):
    __slots__ = ('_configurator', )

    def __init__(self, **kwargs):
        from .configurator import FullStackApplicationConfigurator
        self._configurator = FullStackApplicationConfigurator()
        self._configurator.update_blueprint(kwargs)

        def _on_config_ready(_, conf):
            self.after_init_config(conf)
        tg.hooks.register('initialized_config', _on_config_ready)

        def _startup_hook(*args, **kwargs):
            tg.hooks.notify('startup', trap_exceptions=True)
        tg.hooks.register('initialized_config', _startup_hook)

        def _before_config_hook(app):
            return tg.hooks.notify_with_value('before_config', app)
        tg.hooks.register('before_wsgi_middlewares', _before_config_hook)

        def _after_config_hook(app):
            return tg.hooks.notify_with_value('after_config', app)
        tg.hooks.register('after_wsgi_middlewares', _after_config_hook)

    def after_init_config(self, conf):
        """
        Override this method to set up configuration variables at the application
        level.  This method will be called after your configuration object has
        been initialized on startup.  Here is how you would use it to override
        the default setting of tg.strict_tmpl_context ::

            from tg import Configurator

            class MyAppConfigurator(Configurator):
                def after_init_config(self, conf):
                    conf['tg.strict_tmpl_context'] = False

            base_config = MyAppConfig()

        """
        pass

    def __setitem__(self, key, value):
        self._configurator.update_blueprint({key: value})

    def __getitem__(self, item):
        return self._configurator.get_blueprint_value(item)

    def get_view(self, item):
        return self._configurator.get_blueprint_view(item)

    def __setattr__(self, key, value):
        if key not in self.__slots__:
            self.__setitem__(key, value)
        else:
            object.__setattr__(self, key, value)
        return value

    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(item)

    def register_application_wrapper(self, wrapper, after=None):
        self._configurator.register_application_wrapper(wrapper, after)

    def register_engine(self, factory):
        self._configurator.get('rendering').register_engine(factory)

    def make_load_environment(self):
        """Return a load_environment function.

        The returned load_environment function can be called to configure
        the TurboGears runtime environment for this particular application.
        You can do this dynamically with multiple nested TG applications
        if necessary.

        """
        return self._configurator.load_environment

    def setup_tg_wsgi_app(self, load_environment=None):
        """Create a base TG app, with all the standard middleware.

        ``load_environment``
            A required callable, which sets up the basic evironment
            needed for the application.
        ``setup_vars``
            A dictionary with all special values necessary for setting up
            the base wsgi app.

        """

        def make_base_app(global_conf=None, wrap_app=None, **app_conf):
            # Configure the Application environment
            init_config = load_environment
            if init_config is None:
                init_config = self.make_load_environment()

            return self._configurator.make_app(init_config(global_conf or {}, app_conf),
                                               wrap_app)

        return make_base_app

    def make_wsgi_app(self, **kwargs):
        return self._configurator.make_wsgi_app(**kwargs)


class OldAppConfig(Bunch):
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
    }

    def __init__(self, minimal=False, root_controller=None):
        """Creates some configuration defaults"""
        self.enable_routing_args = False
        self.disable_request_extensions = minimal

        # Registry for functions to be called on startup/teardown
        self.call_on_startup = []
        self.call_on_shutdown = []
        self.controller_caller = call_controller
        self.controller_wrappers = []
        self.application_wrappers = DependenciesList()

    def _init_config(self, global_conf, app_conf):
        """Initialize the config object.

        Besides basic initialization, this method copies all the values
        in base_config into the ``tg.config`` objects.

        """
        # Load the mimetypes with its default types

        conf = {}

        # Load the errorware configuration from the Paste configuration file
        # These all have defaults, and emails are only sent if configured and
        # if this application is running in production mode
        errorware = {}
        errorware['debug'] = conf['debug']

        conf['tg.errorware'] = errorware

        return conf

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

            if app_config.get('make_body_seekable', False):
                app = self._add_seekable_body_middleware(app_config, app)

            if asbool(full_stack):
                # This should never be true for internal nested apps
                app = self._add_slowreqs_middleware(app_config, app)
                app = self._add_error_middleware(app_config, app)

            # Place the debuggers after the registry so that we
            # can preserve context in case of exceptions
            app = self._add_debugger_middleware(app_config, app)

            app = tg.hooks.notify_with_value('after_config', app)

            return app

        return make_base_app

