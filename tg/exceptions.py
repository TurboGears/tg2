"""http exceptions for TurboGears

TurboGears http exceptions are inherited from WebOb http exceptions
"""
import webob
from webob.exc import *


class _HTTPMoveLazyLocation(object):
    """
    
    """
    def __init__(self, *args, **kw):
        try:
            kw['location'] = str(kw['location'])
        except KeyError:
            pass
        super(_HTTPMoveLazyLocation, self).__init__(*args, **kw)


class HTTPMovedPermanently(_HTTPMoveLazyLocation, webob.exc.HTTPMovedPermanently):
    """
    subclass of :class:`webob.exc.HTTPMovedPermanently` with
    support for lazy strings as location.

    This indicates that the requested resource has been assigned a new
    permanent URI and any future references to this resource SHOULD use
    one of the returned URIs.

    code: 301, title: Moved Permanently
    """


class HTTPFound(_HTTPMoveLazyLocation, webob.exc.HTTPFound):
    """
    subclass of :class:`webob.exc.HTTPFound` with
    support for lazy strings as location.

    This indicates that the requested resource resides temporarily under
    a different URI.

    code: 302, title: Found
    """


class HTTPTemporaryRedirect(_HTTPMoveLazyLocation, webob.exc.HTTPTemporaryRedirect):
    """
    subclass of :class:`webob.exc.HTTPTemporaryRedirect` with
    support for lazy strings as location.

    This indicates that if the client has performed a conditional GET
    request and access is allowed, but the document has not been
    modified, the server SHOULD respond with this status code.

    code: 304, title: Not Modified
    """
