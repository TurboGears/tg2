from tg.request_local import Request, Response

import logging
log = logging.getLogger(__name__)


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
