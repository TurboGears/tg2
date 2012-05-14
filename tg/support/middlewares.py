from tg.request_local import Request, Response
from tg.support.registry import StackedObjectProxy

def call_wsgi_application(application, environ, catch_exc_info=False):
    """
    Call the given WSGI application, returning ``(status_string,
    headerlist, app_iter)``

    Be sure to call ``app_iter.close()`` if it's there.

    If catch_exc_info is true, then returns ``(status_string,
    headerlist, app_iter, exc_info)``, where the fourth item may
    be None, but won't be if there was an exception.  If you don't
    do this and there was an exception, the exception will be
    raised directly.

    """
    captured = []
    output = []
    def start_response(status, headers, exc_info=None):
        if exc_info is not None and not catch_exc_info:
            raise (exc_info[0], exc_info[1], exc_info[2])
        captured[:] = [status, headers, exc_info]
        return output.append
    app_iter = application(environ, start_response)
    if not captured or output:
        try:
            output.extend(app_iter)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        app_iter = output
    if catch_exc_info:
        return (captured[0], captured[1], app_iter, captured[2])
    else:
        return (captured[0], captured[1], app_iter)

class StatusCodeRedirect(object):
    """Internally redirects a request based on status code

    StatusCodeRedirect watches the response of the app it wraps. If the
    response is an error code in the errors sequence passed the request
    will be re-run with the path URL set to the path passed in.

    This operation is non-recursive and the output of the second
    request will be used no matter what it is.

    Should an application wish to bypass the error response (ie, to
    purposely return a 401), set
    ``environ['tg.status_code_redirect'] = True`` in the application.

    """
    def __init__(self, app, errors=(400, 401, 403, 404),
                 path='/error/document'):
        """Initialize the ErrorRedirect

        ``errors``
            A sequence (list, tuple) of error code integers that should
            be caught.
        ``path``
            The path to set for the next request down to the
            application.

        """
        self.app = app
        self.error_path = path

        # Transform errors to str for comparison
        self.errors = tuple([str(x) for x in errors])

    def __call__(self, environ, start_response):
        status, headers, app_iter, exc_info = call_wsgi_application(self.app, environ, catch_exc_info=True)
        if status[:3] in self.errors and \
            'tg.status_code_redirect' not in environ and self.error_path:
            # Create a response object
            environ['tg.original_response'] = Response(status=status, headerlist=headers, app_iter=app_iter)
            environ['tg.original_request'] = Request(environ)

            environ['pylons.original_response'] = environ['tg.original_response']
            environ['pylons.original_request'] = environ['tg.original_request']
            
            # Create a new environ to avoid touching the original request data
            new_environ = environ.copy()
            new_environ['PATH_INFO'] = self.error_path

            newstatus, headers, app_iter, exc_info = call_wsgi_application(
                    self.app, new_environ, catch_exc_info=True)
        start_response(status, headers, exc_info)
        return app_iter

from beaker.middleware import CacheMiddleware as BeakerCacheMiddleware
from beaker.middleware import SessionMiddleware as BeakerSessionMiddleware

class SessionMiddleware(BeakerSessionMiddleware):
    session = StackedObjectProxy(name="Beaker Session")

class CacheMiddleware(BeakerCacheMiddleware):
    cache = StackedObjectProxy(name="Cache Manager")

from .statics import StaticsMiddleware

__all__ = ['StatusCodeRedirect', 'CacheMiddleware', 'SessionMiddleware', 'StaticsMiddleware']