from __future__ import absolute_import

from ..support.registry import Registry
from ..request_local import request, Response, config, context
from ..wsgiapp import TGApp


def test_context(app, url=None, environ=None):
    """Sets up a TurboGears context allowing to use turbogears functions outside of a real request.

    Everything inside the with statement will have a TurboGears context available

    In case ``app`` is a ``TGApp`` instance (as the one that can be retrieved
    through `configure_new_app` hook) a context for such application is set in place.

    In case of a WebTest application a request to ``/_test_vars`` is performed
    to setup the test variables.

    In case ``app`` is ``None`` a fake application is created for which to setup the context.

    ``url`` parameter is provided to simulate the context as being for that url and
    ``environ`` parameter is provided to allow changing WSGI environ entries for the
    context.
    """
    if app is None:
        app = _BareTGAppMaker().make()

    url = url or '/'

    from webob.request import environ_from_url
    wsgienviron = environ_from_url(url)
    wsgienviron.update(environ or {})

    if isinstance(app, TGApp):
        return _TGTestContextManager(app, wsgienviron)
    else:
        return _WebTestTGTestContextManager(app, wsgienviron)

test_context.__test__ = False  # Prevent nose from detecting this as a test.


class _BareTGAppMaker(object):
    """Makes a new TGApp and returns it without any surrounding middleware."""
    def __init__(self):
        self.app = None

    def set_app(self, app):
        self.app = app
        return app

    def make(self):
        from ..configurator import MinimalApplicationConfigurator
        configurator = MinimalApplicationConfigurator()
        configurator.update_blueprint({
            'root_controller': lambda *args: Response('HELLO')
        })
        configurator.make_wsgi_app(wrap_app=self.set_app)
        return self.app


class _TGTestContextManager(object):
    """Provides a context manager to setup thread local context for a TGApp"""
    def __init__(self, app, environ):
        self._app = app
        self._environ = environ
        self._registry = Registry()
        self._registry.prepare()
        self._environ['paste.registry'] = self._registry

    def __enter__(self):
        self._app._setup_app_env(self._environ)
        return self._app

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._registry.cleanup()


class _WebTestTGTestContextManager(object):
    """Provides a context manager to setup thread local context for a WebTest TG app."""
    def __init__(self, app, environ):
        self._app = app
        self._environ = environ

    def __enter__(self):
        self._app.get('/_test_vars')
        request.environ.update(self._environ)
        return self._app

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            config._pop_object()
        except AssertionError:
            pass

        try:
            context._pop_object()
        except AssertionError:
            pass