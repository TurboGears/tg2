# -*- coding: utf-8 -*-
import logging

from ...util import Bunch
from .base import Configurator
from .base import EnvironmentLoadedConfigurationAction, AppReadyConfigurationAction
from ..hooks import hooks
from .. import milestones
from ...wsgiapp import TGApp
from ..utils import DependenciesList
from ...request_local import config as reqlocal_config


log = logging.getLogger(__name__)


class ApplicationConfigurator(Configurator):
    def __init__(self):
        super(ApplicationConfigurator, self).__init__()

        self._application_wrappers = DependenciesList()

    def configure(self, global_conf=None, app_conf=None):
        global_conf = Bunch(global_conf or {})
        app_conf = Bunch(app_conf or {})

        conf = super(ApplicationConfigurator, self).configure(global_conf, app_conf)

        # Application wrapper are made available in the configuration for TGApp use.
        conf['application_wrappers'] = self._application_wrappers

        # Load conf dict into the global config object
        try:
            reqlocal_config.pop_process_config()
        except IndexError:  # pragma: no cover
            log.warn('No global config in place, at least defaults should have been here')
        finally:
            reqlocal_config.push_process_config(conf)

        milestones.config_ready.reach()
        hooks.notify('initialized_config', args=(self, conf))
        return conf

    def load_environment(self, global_conf, app_conf):
        """Configure a TurboGears Application environment.

        ``global_conf``
            The inherited configuration for this application. Normally
            from the [DEFAULT] section of the Paste ini file.

        ``app_conf``
            The application's local configuration. Normally specified in
            the [app:<name>] section of the Paste ini file (where <name>
            defaults to main).
        """
        conf = self.configure(global_conf, app_conf)

        self.setup(conf)
        hooks.notify('config_setup', args=(self, conf))

        # Trigger milestone here so that it gets triggered even when
        # websetup (setup-app command) is performed.
        milestones.environment_loaded.reach()

        return conf

    def make_app(self, conf, wrap_app=None):
        """Create a tg WSGI application and return it.

        ``conf``
            The application's configuration returned by the
            Configurator

        ``wrap_app``
            a WSGI middleware component which takes the core turbogears
            application and wraps it -- inside all the WSGI-components
            provided by TG. This allows you to work with the
            full environment that your TG application would get before
            anything happens in the application itself.

        """
        for _, step in self._steps:
            step._apply(EnvironmentLoadedConfigurationAction, conf)

        app = TGApp(conf)

        hooks.notify('configure_new_app', args=(app,))

        if wrap_app is not None:
            app = wrap_app(app)

        app = hooks.notify_with_value('before_wsgi_middlewares', app)

        for _, step in self._steps:
            app = step._apply(AppReadyConfigurationAction, conf, app)

        app = hooks.notify_with_value('after_wsgi_middlewares', app)

        return app

    def make_wsgi_app(self, **app_conf):
        # wrap_app is an argument to make_app, not a configuration option.
        wrap_app = app_conf.pop('wrap_app', None)

        conf = self.load_environment({}, app_conf)
        return self.make_app(conf, wrap_app=wrap_app)

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
            log.warning('Application Wrapper %s registered after environment loaded'
                        'milestone has been reached, the wrapper will be used only'
                        'for future TGApp instances.', wrapper)

        log.debug('Registering application wrapper: %s', wrapper)
        self._application_wrappers.add(wrapper, after=after)

    def replace_application_wrapper(self, key, wrapper):
        self._application_wrappers.replace(key, wrapper)
