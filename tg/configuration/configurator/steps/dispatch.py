# -*- coding: utf-8 -*-
from tg.configuration import milestones
from ..base import ConfigurationStep, BeforeConfigConfigurationAction, \
    EnvironmentLoadedConfigurationAction

from logging import getLogger
log = getLogger(__name__)


class DispatchConfigurationStep(ConfigurationStep):
    """
        - root_controller
        - disable_request_extensions
        - dispatch_path_translator
        - ignore_parameters
        - enable_routing_args
    """
    id = "dispatch"

    def __init__(self):
        super(DispatchConfigurationStep, self).__init__()
        self._controller_wrappers = []

    def get_defaults(self):
        return {
            'enable_routing_args': False,
            'disable_request_extensions': False
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_explicit_root_controller),
            EnvironmentLoadedConfigurationAction(self._setup_controller_wrappers)
        )

    def _configure_explicit_root_controller(self, conf, app):
        conf['tg.root_controller'] = conf.pop('root_controller', None)

    def _setup_controller_wrappers(self, conf, app):
        # This trashes away the current config['controller_caller']
        # so that the call is idempotent.
        base_controller_caller = _call_controller

        controller_caller = base_controller_caller
        for wrapper in self._controller_wrappers:
            controller_caller = wrapper(controller_caller)

        conf['controller_caller'] = controller_caller

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
            log.warning('Controller Wrapper %s registered after environment loaded '
                        'milestone has been reached, the wrapper will be used only '
                        'for future TGApp instances.', wrapper)

        log.debug("Registering %s controller wrapper for controller: %s",
                  wrapper, controller or 'ALL')

        if controller is None:
            self._controller_wrappers.append(wrapper)
        else:
            from tg.decorators import Decoration
            deco = Decoration.get_decoration(controller)
            deco._register_controller_wrapper(wrapper)


def _call_controller(tg_config, controller, remainder, params):
    return controller(*remainder, **params)

