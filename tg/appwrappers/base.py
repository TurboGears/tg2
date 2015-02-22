from abc import ABCMeta, abstractmethod
from .._compat import with_metaclass
from ..caching import cached_property


class ApplicationWrapper(with_metaclass(ABCMeta)):
    """Basic interface of the TurboGears Application Wrappers.

    Application wrappers are like WSGI middlewares but
    are executed in the context of TurboGears and work
    with abstractions like Request and Respone objects.

    Application Wrappers can be registered using
    :meth:`.AppConfig.register_wrapper` which will inject
    them into the next `TGApp` created.

    While they can be any callable, inheriting from this base class
    is strongly suggested as enables additional behaviours and
    third party code might depend on them.

    Application Wrappers require a ``next_handler`` which is
    the next handler to call in the chain and ``config`` which
    is the current application configuration.

    """
    def __init__(self, next_handler, config):
        self._next_handler = next_handler

    @cached_property
    def next_handler(self):
        """The next handler in the chain"""
        return self._next_handler

    @property
    def injected(self):  # pragma: no cover
        """Whenever the Application Wrapper should be injected.

        By default all application wrappers are injected into the
        wrappers chain, you might want to make so that they are injected
        or not depending on configuration options.

        """
        return True

    @abstractmethod
    def __call__(self, controller, environ, context):  # pragma: no cover
        """This is the actual wrapper implementation.

        Wrappers are called for each request with the ``controller`` in charge
        of handling the request, the ``environ`` of the request and the
        TurboGears ``context`` of the request.

        They should call the ``next_handler`` (which will accept the same
        parameters) and return a :class:`tg.request_local.Response` instance
        which is the request response.
        Usually they will return the same response object provided
        by the next handler unless they want to replace it.

        A simple logging wrapper might look like::

            class LogAppWrapper(ApplicationWrapper):
                def __init__(self, handler, config):
                    super(LogAppWrapper, self).__init__(handler, config)

                def __call__(self, controller, environ, context):
                    print 'Going to run %s' % context.request.path
                    return self.next_handler(controller, environ, context)

        """
        raise NotImplementedError

