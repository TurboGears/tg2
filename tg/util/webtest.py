from __future__ import absolute_import
from ..request_local import request, Response, config, context


class test_context(object):
    """Given a WebTest application, performs a ``with`` statement using ``/_test_vars``.

    if ``app`` is ``None`` a new empty application is configured which responds 'HELLO'
    to every request.

    Entering the context a request for ``/_test_vars`` is performed such to setup the
    test variables, everything inside the with statement has a TurboGears context available
    which is then removed by a call to ``/`` at the end of the ``with`` block to reset
    the test variables.

    ``url`` parameter is provided to simulate the context as being for that url and
    ``environ`` parameter is provided to allow changing WSGI environ entries for the
    context.
    """
    def __init__(self, app, url=None, environ=None):
        if app is None:
            from webtest import TestApp
            from ..configuration.app_config import AppConfig
            app = TestApp(AppConfig(
                minimal=True,
                root_controller=lambda *args: Response('HELLO')
            ).make_wsgi_app())

        self._app = app
        self._environ = environ
        self._url = url

    def __enter__(self):
        self._app.get('/_test_vars')

        if self._url is not None:
            from webob.request import environ_from_url
            request.environ.update(environ_from_url(self._url))

        if self._environ is not None:
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