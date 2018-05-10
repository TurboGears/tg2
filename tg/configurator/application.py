# -*- coding: utf-8 -*-
import logging

from ..util import Bunch
from .base import Configurator
from .base import EnvironmentLoadedConfigurationAction, AppReadyConfigurationAction
from ..configuration.hooks import hooks
from .. import milestones
from ..wsgiapp import TGApp
from ..configuration.utils import DependenciesList
from ..request_local import config as reqlocal_config


log = logging.getLogger(__name__)


class ApplicationConfigurator(Configurator):
    """A Configurator specialised in creating TurboGears applications.

    The configuration blueprint will be used as configuration foundation
    for every new application built from the Configurator, configuration
    blueprint is merged with deployment configuration loaded from
    config files before creating the application.

    Refer to each registered configuration component for
    configuration options available in the Configurator.

    .. versionadded:: 2.4
    """
    def __init__(self):
        super(ApplicationConfigurator, self).__init__()
        self._application_wrappers = DependenciesList()

    def configure(self, global_conf=None, app_conf=None):
        """Initializes configuration of the application.

        Applies all the blueprints, components defaults, global_conf, app_confg
        and components coercions then returns the resulting configuration.
        Also the configuration is set as the currently active one in the process.

        This is the first step invoked by :meth:`.make_wsgi_app` to create a
        new TurboGears application.
        """
        global_conf = Bunch(global_conf or {})
        app_conf = Bunch(app_conf or {})

        conf = super(ApplicationConfigurator, self).configure(global_conf, app_conf)

        # Application wrapper are made available in the configuration for TGApp use.
        conf['application_wrappers'] = self._application_wrappers

        # Load conf dict into the global config object
        try:
            reqlocal_config.pop_process_config()
        except IndexError:  # pragma: no cover
            log.warning('No global config in place, at least defaults should have been here')
        finally:
            reqlocal_config.push_process_config(conf)

        milestones.config_ready.reach()
        hooks.notify('initialized_config', args=(self, conf))
        return conf

    def setup(self, conf):
        """Setup a TurboGears application environment given a configuration.

        This usually involves any configuration step that requires
        all configuration options to be available before it can be executed.

        It's also the place where ApplicationWrappers and ControllerWrappers
        are resolved.
        """
        super(ApplicationConfigurator, self).setup(conf)
        hooks.notify('config_setup', args=(self, conf))

        # Trigger milestone here so that it gets triggered even when
        # websetup (setup-app command) is performed.
        milestones.environment_loaded.reach()

        for _, step in self._components:
            step._apply(EnvironmentLoadedConfigurationAction, conf)

    @classmethod
    def current(self):
        """Retrieves the current ApplicationConfigurator given that a configuration is in place.

        The current configurator is saved within the configuration itself, so whenever
        a configuration is in place it is possible to get access to the configurator
        and then access any of its componenets::

            ApplicationConfigurator.current().get('componentid')
        """
        configurator = reqlocal_config['tg.configurator']()
        return configurator

    def _make_app(self, conf, wrap_app=None):
        """Create a tg WSGI application and return it.

        ``conf``
            The application's configuration returned by the
            Configurator after :meth:`.configure` and :meth:`.setup`
            were already applied.

        ``wrap_app``
            a WSGI middleware component which takes the core turbogears
            application and wraps it -- inside all the WSGI-components
            provided by TG. This allows you to work with the
            full environment that your TG application would get before
            anything happens in the application itself.

        """
        app = TGApp(conf)

        hooks.notify('configure_new_app', args=(app,))

        if wrap_app is not None:
            app = wrap_app(app)

        app = hooks.notify_with_value('before_wsgi_middlewares', app)

        for _, step in self._components:
            app = step._apply(AppReadyConfigurationAction, conf, app)

        app = hooks.notify_with_value('after_wsgi_middlewares', app)

        return app

    def make_wsgi_app(self, global_conf=None, app_conf=None, wrap_app=None):
        """Creates a new WSGI TurboGears application with provided configuration."""
        conf = self.configure(global_conf, app_conf)
        self.setup(conf)
        return self._make_app(conf, wrap_app=wrap_app)

    def register_application_wrapper(self, wrapper, after=None):
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
            log.warning('Application Wrapper %s registered after environment loaded '
                        'milestone has been reached, the wrapper will be used only '
                        'for future TGApp instances.', wrapper)

        log.debug('Registering application wrapper: %s', wrapper)
        self._application_wrappers.add(wrapper, after=after)

    def replace_application_wrapper(self, key, wrapper):
        """Replaces a registered application wrapper with another one.

        Note that this only applies to future applications that will be created,
        not to already existing ones.
        """
        self._application_wrappers.replace(key, wrapper)
