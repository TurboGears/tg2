# -*- coding: utf-8 -*-
"""
Utilities for TurboGears hooks management.

Provides a consistent API to register and execute hooks.

"""
import atexit
import warnings
from .utils import TGConfigError
from .milestones import config_ready, renderers_ready, environment_loaded
from ..decorators import Decoration
from .._compat import default_im_func
from .app_config import config as tg_config


from logging import getLogger
log = getLogger(__name__)


class HooksNamespace(object):
    """Manages hooks registrations and notifications"""
    def __init__(self):
        self._hooks = dict()
        atexit.register(self._atexit)

    def _atexit(self):
        for func in self._hooks.get('shutdown', tuple()):
            func()

    def _call_handler(self, hook_name, trap_exceptions, func, args, kwargs):
        try:
            return func(*args, **kwargs)
        except:
            if trap_exceptions is True:
                log.exception('Trapped Exception while handling %s -> %s', hook_name, func)
            else:
                raise

    def register(self, hook_name, func, controller=None):
        """Registers a TurboGears hook.

        Given an hook name and a function it registers the provided
        function for that role. For a complete list of hooks
        provided by default have a look at :ref:`hooks_and_events`.

        It permits to register hooks both application wide
        or for specific controllers::

            tg.hooks.register('before_render', hook_func, controller=RootController.index)
            tg.hooks.register('startup', startup_function)

        """
        if hook_name in ('startup', 'shutdown') and controller is not None:
            raise TGConfigError('Startup and Shutdown hooks cannot be registered on controllers')

        if hook_name == 'controller_wrapper':
            raise TGConfigError('tg.hooks.wrap_controller must be used to register wrappers')

        if controller is None:
            config_ready.register(_ApplicationHookRegistration(self, hook_name, func))
        else:
            controller = default_im_func(controller)
            renderers_ready.register(_ControllerHookRegistration(controller, hook_name, func))

    def disconnect(self, hook_name, func, controller=None):
        """Disconnect an hook.

        The registered function is removed from the hook notification list.
        """
        if controller is None:
            registrations = self._hooks.get(hook_name, [])
        else:
            deco = Decoration.get_decoration(controller)
            registrations = deco.hooks.get(hook_name, [])

        try:
            registrations.remove(func)
        except ValueError:
            pass

    def notify(self, hook_name, args=None, kwargs=None, controller=None,
               context_config=None, trap_exceptions=False):
        """Notifies a TurboGears hook.

        Each function registered for the given hook will be executed,
        ``args`` and ``kwargs`` will be passed to the registered functions
        as arguments.

        It permits to notify both application hooks::

            tg.hooks.notify('custom_global_hook')

        Or controller hooks::

            tg.hooks.notify('before_render', args=(remainder, params, output),
                            controller=RootController.index)

        """
        args = args or []
        kwargs = kwargs or {}

        try:
            syswide_hooks = self._hooks[hook_name]
        except KeyError:  # pragma: no cover
            pass
        else:
            for func in syswide_hooks:
                self._call_handler(hook_name, trap_exceptions, func, args, kwargs)

        if controller is not None:
            controller = default_im_func(controller)
            deco = Decoration.get_decoration(controller)
            for func in deco.hooks.get(hook_name, []):
                self._call_handler(hook_name, trap_exceptions, func, args, kwargs)

    def notify_with_value(self, hook_name, value, controller=None, context_config=None):
        """Notifies a TurboGears hook which is expected to return a value.

        hooks with values are expected to accept an input value an return
        a replacement for it. Each registered function will receive as input
        the value returned by the previous function in chain.

        The resulting value will be returned by the ``notify_with_value``
        call itself::

            app = tg.hooks.notify_with_value('before_config', app)

        """
        try:
            syswide_hooks = self._hooks[hook_name]
        except KeyError:  # pragma: no cover
            pass
        else:
            for func in syswide_hooks:
                value = func(value)

        if controller is not None:
            controller = default_im_func(controller)
            deco = Decoration.get_decoration(controller)
            for func in deco.hooks[hook_name]:
                value = func(value)

        return value


class _ApplicationHookRegistration(object):
    def __init__(self, hooks_namespace, hook_name, func):
        self.hook_name = hook_name
        self.func = func
        self.hooks_namespace = hooks_namespace

    def __call__(self):
        log.debug("Registering %s for application wide hook %s",
                  self.func, self.hook_name)

        if self.hook_name == 'controller_wrapper':
            warnings.warn('controller wrappers should be registered on '
                          'AppConfig using AppConfig.register_controller_wrapper',
                          DeprecationWarning)

            config = tg_config._current_obj()
            config['controller_wrappers'].append(self.func)
        else:
            hooks = self.hooks_namespace._hooks
            hooks.setdefault(self.hook_name, []).append(self.func)


class _ControllerHookRegistration(object):
    def __init__(self, controller, hook_name, func):
        self.controller = controller
        self.hook_name = hook_name
        self.func = func

    def __call__(self):
        log.debug("Registering %s for hook %s on controller %s",
                  self.func, self.hook_name, self.controller)

        if self.hook_name == 'controller_wrapper':
            warnings.warn('controller wrappers should be registered on '
                          'AppConfig using AppConfig.register_controller_wrapper',
                          DeprecationWarning)

            deco = Decoration.get_decoration(self.controller)
            deco._register_controller_wrapper(self.func)
        else:
            deco = Decoration.get_decoration(self.controller)
            deco._register_hook(self.hook_name, self.func)


class _TGGlobalHooksNamespace(HooksNamespace):
    def wrap_controller(self, func, controller=None):
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

            tg.hooks.wrap_controller(controller_wrapper)

        It is also possible to register wrappers for a specific controller::

            tg.hooks.wrap_controller(controller_wrapper, controller=RootController.index)

        """
        if environment_loaded.reached:
            raise TGConfigError('Controller wrappers can be registered only at '
                                'configuration time.')

        if controller is None:
            environment_loaded.register(_ApplicationHookRegistration(self,
                                                                     'controller_wrapper',
                                                                     func))
        else:
            controller = default_im_func(controller)
            registration = _ControllerHookRegistration(controller, 'controller_wrapper', func)
            renderers_ready.register(registration)

hooks = _TGGlobalHooksNamespace()
