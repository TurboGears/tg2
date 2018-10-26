# -*- coding: utf-8 -*-
"""
Utilities for TurboGears hooks management.

Provides a consistent API to register and execute hooks.

"""
import atexit
from .utils import TGConfigError
from .milestones import config_ready, renderers_ready
from ..controllers.decoration import Decoration
from .._compat import default_im_func


from logging import getLogger
log = getLogger(__name__)


class HooksNamespace(object):
    """Manages hooks registrations and notifications"""
    def __init__(self):
        self._hooks = dict()
        atexit.register(self._atexit)

    def _clear(self):
        self._hooks.clear()

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
        if controller is not None and hook_name in ('startup', 'shutdown',
                                                    'initialized_config',
                                                    'before_wsgi_middlewares',
                                                    'after_wsgi_middlewares'):
            raise TGConfigError('Startup and Shutdown hooks cannot be registered on controllers')

        if hook_name == 'controller_wrapper':
            raise ValueError('dispatch component must be used to register controller wrappers')

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
               trap_exceptions=False):
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

    def notify_with_value(self, hook_name, value, controller=None):
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

    def __repr__(self):
        return '<ApplicationHookRegistration: %r %r>' % (self.hook_name, self.func)

    def __call__(self):
        log.debug("Registering %s for application wide hook %s",
                  self.func, self.hook_name)
        hooks = self.hooks_namespace._hooks
        hooks.setdefault(self.hook_name, []).append(self.func)


class _ControllerHookRegistration(object):
    def __init__(self, controller, hook_name, func):
        self.controller = controller
        self.hook_name = hook_name
        self.func = func

    def __repr__(self):
        return '<ControllerHookRegistration: %r %r>' % (self.hook_name, self.func)

    def __call__(self):
        log.debug("Registering %s for hook %s on controller %s",
                  self.func, self.hook_name, self.controller)
        deco = Decoration.get_decoration(self.controller)
        deco._register_hook(self.hook_name, self.func)


class _TGGlobalHooksNamespace(HooksNamespace):
    pass

hooks = _TGGlobalHooksNamespace()
