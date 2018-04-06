"""Configuration Helpers for TurboGears 2"""
import logging
import tg
from tg.util import Bunch

log = logging.getLogger(__name__)


class AppConfig(object):
    __slots__ = ('_configurator', )

    # Attributes and properties that are automatically returned as a view
    # This mostly handles backward compatibility with some oddities of
    # TG<2.4 where some config properties where flat and some were subdicts.
    VIEWS_ATTRIBUTES = set(('sa_auth', ))

    def __init__(self, **kwargs):
        from .configurator import FullStackApplicationConfigurator
        self._configurator = FullStackApplicationConfigurator()

        if kwargs.pop('minimal', False):
            self._configurator.update_blueprint({
                'i18n.enabled': False,
                'session.enabled': False,
                'auth_backend': None,
                'cache.enabled': False,
                'tw2.enabled': False,
                'use_ming': False,
                'use_sqlalchemy': False,
                'tm.enabled': False,
                'errorpage.enabled': False,
                'make_body_seekable': False,
                'trace_slowreqs.enable': False,
                'trace_errors.enable': False,
                'serve_static': False,
                'debug': False
            })
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
        if key in self.VIEWS_ATTRIBUTES:
            self.get_view(key).update(value)
        else:
            self._configurator.update_blueprint({key: value})

    def __getitem__(self, item):
        if item in self.VIEWS_ATTRIBUTES:
            return self.get_view(item)
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

    def register_wrapper(self, wrapper, after=None):
        self._configurator.register_application_wrapper(wrapper, after)

    def register_rendering_engine(self, factory):
        self._configurator.get('rendering').register_engine(factory)

    def register_controller_wrapper(self, wrapper, controller=None):
        self._configurator.get('dispatch').register_controller_wrapper(wrapper, controller)

    def make_load_environment(self):
        """Return a load_environment function.

        The returned load_environment function can be called to configure
        the TurboGears runtime environment for this particular application.
        You can do this dynamically with multiple nested TG applications
        if necessary.

        """
        def _load_environment(global_conf, app_conf):
            conf = self._configurator.configure(global_conf, app_conf)
            self._configurator.setup(conf)
            return conf
        return _load_environment

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
            return self._configurator._make_app(init_config(global_conf or {}, app_conf),
                                                wrap_app)
        return make_base_app

    def make_wsgi_app(self, **kwargs):
        # wrap_app is an argument to make_wsgi_app, not a configuration option.
        wrap_app = kwargs.pop('wrap_app', None)
        return self._configurator.make_wsgi_app({}, kwargs, wrap_app=wrap_app)


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
        - ``registry_streaming`` -> Enable streaming of responses, this is enabled by default.
          **Can be set from .ini file**
        - ``use_toscawidgets`` -> Enable ToscaWidgets1, this is deprecated.
        - ``use_toscawidgets2`` -> Enable ToscaWidgets2
        - ``prefer_toscawidgets2`` -> When both TW2 and TW1 are enabled prefer TW2. **Can be set from .ini file**
        - ``custom_tw2_config`` -> Dictionary of configuration options for TW2, refer to
          :class:`.tw2.core.middleware.Config` for available options.
        - ``auth_backend`` -> Authentication Backend, can be ``None``, ``sqlalchemy`` or ``ming``.
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
    pass