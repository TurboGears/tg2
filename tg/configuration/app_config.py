"""Configuration Helpers for TurboGears 2"""
import logging
import warnings

import tg

log = logging.getLogger(__name__)


class AppConfig(object):
    """Backward compatible Application Configurator.

    This allows to configure a TurboGears2 application in a way
    that is compatible with existing >=2.1,<=2.3 applications.

    All the attributes and keys you will set into the AppConfig
    will be used to build the blueprint used by a
    :class:`.FullStackApplicationConfigurator`
    to configure a new :class:`.TGApp`.

    .. deprecated:: 2.4.0
        Use :class:`.FullStackApplicationConfigurator` instead.
    """
    __slots__ = ('_configurator', )

    # Attributes and properties that are automatically returned as a view
    # This mostly handles backward compatibility with some oddities of
    # TG<2.4 where some config properties where flat and some were subdicts.
    VIEWS_ATTRIBUTES = set(('sa_auth', ))

    def __init__(self, **kwargs):
        from ..configurator import FullStackApplicationConfigurator
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

    def get(self, k, d=None):
        try:
            return self[k]
        except KeyError:
            return d

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

    def register_hook(self, hookname, handler, controller=None):
        tg.hooks.register(hookname, handler, controller=controller)

    def register_wrapper(self, wrapper, after=None):
        self._configurator.register_application_wrapper(wrapper, after)

    def register_rendering_engine(self, factory):
        self._configurator.get_component(
            'rendering'
        ).register_engine(factory)

    def register_controller_wrapper(self, wrapper, controller=None):
        self._configurator.get_component(
            'dispatch'
        ).register_controller_wrapper(wrapper, controller)

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
        """Creates a TGApp Factory, with the required load_environment.

        ``load_environment``
            A callable, which sets up the basic evironment
            needed for the application. A default environment is configured otherwise.

        The returned factory function accepts:

            * ``global_conf``: Dictionary with options that should be added to configuration.
            * ``wrap_app``: A function that can wrap application and return a new WSGI app.
            * ``**app_conf``: Keyword arguments that will be passed as configuration options.

        """
        warnings.warn("Using AppConfig to create apps is deprecated in favor of "
                      "tg.FullStackApplicationConfigurator and will be removed.",
                      DeprecationWarning)

        def make_base_app(global_conf=None, wrap_app=None, **app_conf):
            # Configure the Application environment
            init_config = load_environment
            if init_config is None:
                init_config = self.make_load_environment()
            return self._configurator._make_app(init_config(global_conf or {}, app_conf),
                                                wrap_app)
        return make_base_app

    def make_wsgi_app(self, **kwargs):
        """Creates a new TGApp.

        Only accepted argument is ``wrap_app`` as a keyword argument,
        that can be a callable used to wrap the TGApp in middlewares and
        return a new WSGI application.

        All remaining ``kwargs`` will be added as configuration options to the
        application in addition to those specified in ``AppConfig`` itself.

        """
        warnings.warn("Using AppConfig to create apps is deprecated in favor of "
                      "tg.FullStackApplicationConfigurator and will be removed.",
                      DeprecationWarning)

        # wrap_app is an argument to make_wsgi_app, not a configuration option.
        wrap_app = kwargs.pop('wrap_app', None)
        return self._configurator.make_wsgi_app({}, kwargs, wrap_app=wrap_app)
