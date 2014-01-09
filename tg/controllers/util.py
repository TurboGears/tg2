# -*- coding: utf-8 -*-
"""Helper functions for controller operation.

URL definition and browser redirection are defined here.

"""
import re
from webob.exc import status_map

import tg

from tg._compat import string_type, url_encode, unicode_text, bytes_
from tg.exceptions import HTTPFound

def _smart_str(s):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.

    This function was borrowed from Django.

    """
    if not isinstance(s, string_type):
        try:
            return bytes_(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([_smart_str(arg).decode('utf-8') for arg in s.args]).encode('utf-8', 'strict')
            return unicode_text(s).encode('utf-8', 'strict')
    elif isinstance(s, unicode_text):
        return s.encode('utf-8', 'strict')
    else:
        return s


def _generate_smart_str(params):
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                yield _smart_str(key), _smart_str(item)
        else:
            yield _smart_str(key), _smart_str(value)


def _urlencode(params):
    """
    A version of Python's urllib.urlencode() function that can operate on
    unicode strings. The parameters are first case to UTF-8 encoded strings and
    then encoded as per normal.
    """
    return url_encode([i for i in _generate_smart_str(params)])

def _build_url(environ, base_url='/', params=None):
    if base_url.startswith('/'):
        base_url = environ['SCRIPT_NAME'] + base_url

    if params:
        return '?'.join((base_url, _urlencode(params)))

    return base_url

def url(base_url='/', params=None, qualified=False):
    """Generate an absolute URL that's specific to this application.

    The URL function takes a string (base_url) and, appends the
    SCRIPT_NAME and adds parameters for all of the
    parameters passed into the params dict.

    """
    if not isinstance(base_url, string_type) and hasattr(base_url, '__iter__'):
        base_url = '/'.join(base_url)

    req = tg.request._current_obj()
    base_url = _build_url(req.environ, base_url, params)
    if qualified:
        base_url = req.host_url + base_url

    return base_url


class LazyUrl(object):
    """
    Wraps tg.url in an object that enforces evaluation of the url
    only when you try to display it as a string.
    """

    def __init__(self, base_url, params=None):
        self.base_url = base_url
        self.params = params
        self._decoded = None

    @property
    def _id(self):
        if self._decoded == None:
            self._decoded = url(self.base_url, params=self.params)
        return self._decoded

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return self._id

    def __html__(self):
        return str(self)

    def __str__(self):
        return str(self._id)

    def encode(self, *args, **kw):
        return self._id.encode(*args, **kw)

    def __add__(self, other):
        return self._id + other

    def __radd__(self, other):
        return other + self._id

    def startswith(self, *args, **kw):
        return self._id.startswith(*args, **kw)

    def format(self, other):
        return self._id.format(other)

    def __json__(self):
        return str(self)

def lurl(base_url=None, params=None):
    """
    Like tg.url but is lazily evaluated.

    This is useful when creating global variables as no
    request is in place.

    As without a request it wouldn't be possible
    to correctly calculate the url using the SCRIPT_NAME
    this demands the url resolution to when it is
    displayed for the first time.
    """
    return LazyUrl(base_url, params)


def redirect(base_url='/', params={}, redirect_with=HTTPFound, **kwargs):
    """Generate an HTTP redirect.

    The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the
    second request.
    """

    if kwargs:
        params = params.copy()
        params.update(kwargs)

    new_url = url(base_url, params=params)
    raise redirect_with(location=new_url)

IF_NONE_MATCH = re.compile('(?:W/)?(?:"([^"]*)",?\s*)')
def etag_cache(key=None):
    """Use the HTTP Entity Tag cache for Browser side caching

    If a "If-None-Match" header is found, and equivilant to ``key``,
    then a ``304`` HTTP message will be returned with the ETag to tell
    the browser that it should use its current cache of the page.

    Otherwise, the ETag header will be added to the response headers.
    """
    if_none_matches = IF_NONE_MATCH.findall(tg.request.environ.get('HTTP_IF_NONE_MATCH', ''))
    response = tg.response._current_obj()
    response.headers['ETag'] = '"%s"' % key
    if str(key) in if_none_matches:
        response.headers.pop('Content-Type', None)
        response.headers.pop('Cache-Control', None)
        response.headers.pop('Pragma', None)
        raise status_map[304]()

def abort(status_code=None, detail="", headers=None, comment=None):
    """Aborts the request immediately by returning an HTTP exception

    In the event that the status_code is a 300 series error, the detail
    attribute will be used as the Location header should one not be
    specified in the headers attribute.

    """
    exc = status_map[status_code](detail=detail, headers=headers,
                                  comment=comment)
    raise exc

def use_wsgi_app(wsgi_app):
    return tg.request.get_response(wsgi_app)

__all__ = ['url', 'lurl', 'redirect', 'etag_cache', 'abort']
