from tg.request_local import Request, Response

import logging
log = logging.getLogger(__name__)


def _call_wsgi_application(application, environ):
    """
    Call the given WSGI application, returning ``(status_string,
    headerlist, app_iter)``

    Be sure to call ``app_iter.close()`` if it's there.
    """
    captured = []
    output = []
    def _start_response(status, headers, exc_info=None):
        captured[:] = [status, headers, exc_info]
        return output.append

    app_iter = application(environ, _start_response)
    if not captured or output:
        try:
            output.extend(app_iter)
        finally:
            if hasattr(app_iter, 'close'):
                app_iter.close()
        app_iter = output
    return (captured[0], captured[1], app_iter, captured[2])


class StatusCodeRedirect(object):
    """Internally redirects a request based on status code

    StatusCodeRedirect watches the response of the app it wraps. If the
    response is an error code in the errors sequence passed the request
    will be re-run with the path URL set to the path passed in.

    This operation is non-recursive and the output of the second
    request will be used no matter what it is.

    Should an application wish to bypass the error response (ie, to
    purposely return a 401), set
    ``environ['tg.status_code_redirect'] = False`` in the application.

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
        status, headers, app_iter, exc_info = _call_wsgi_application(self.app, environ)
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

            newstatus, headers, app_iter, exc_info = _call_wsgi_application(self.app, new_environ)
        start_response(status, headers, exc_info)
        return app_iter

try:
    from beaker.middleware import CacheMiddleware as BeakerCacheMiddleware
    from beaker.middleware import SessionMiddleware as BeakerSessionMiddleware
except ImportError:  # pragma: no cover
    # beaker not available
    BeakerCacheMiddleware = object
    BeakerSessionMiddleware = object


class SessionMiddleware(BeakerSessionMiddleware):
    session = None


class CacheMiddleware(BeakerCacheMiddleware):
    cache = None


class SeekableRequestBodyMiddleware(object):
    def __init__(self, app):
        self.app = app

    def _stream_response(self, data):
        try:
            for chunk in data:
                yield chunk
        finally:
            if hasattr(data, 'close'):  # pragma: no cover
                data.close()

    def __call__(self, environ, start_response):
        log.debug("Making request body seekable")
        Request(environ).make_body_seekable()
        return self._stream_response(self.app(environ, start_response))


class DBSessionRemoverMiddleware(object):
    def __init__(self, DBSession, app):
        self.app = app
        self.DBSession = DBSession

    def _stream_response(self, data):
        try:
            for chunk in data:
                yield chunk
        finally:
            log.debug("Removing DBSession from current thread")
            if hasattr(data, 'close'):
                data.close()
            self.DBSession.remove()

    def __call__(self, environ, start_response):
        try:
            return self._stream_response(self.app(environ, start_response))
        except:
            log.debug("Removing DBSession from current thread")
            self.DBSession.remove()
            raise


class MingSessionRemoverMiddleware(object):
    def __init__(self, ThreadLocalODMSession, app):
        self.app = app
        self.ThreadLocalODMSession = ThreadLocalODMSession

    def _stream_response(self, data):
        try:
            for chunk in data:
                yield chunk
        finally:
            log.debug("Removing ThreadLocalODMSession from current thread")
            if hasattr(data, 'close'):
                data.close()
            self.ThreadLocalODMSession.close_all()

    def __call__(self, environ, start_response):
        try:
            return self._stream_response(self.app(environ, start_response))
        except:
            log.debug("Removing ThreadLocalODMSession from current thread")
            self.ThreadLocalODMSession.close_all()
            raise



from .statics import StaticsMiddleware

__all__ = ['StaticsMiddleware', 'SeekableRequestBodyMiddleware',
           'DBSessionRemoverMiddleware', 'MingSessionRemoverMiddleware']
