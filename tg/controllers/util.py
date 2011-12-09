# -*- coding: utf-8 -*-
"""
Helper functions for controller operation.

Url definition and browser redirection are defined here.
"""
import re
from webob.exc import status_map

import tg
import urllib
from warnings import warn

from tg.exceptions import HTTPFound

def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.

    This function was borrowed from Django
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    elif not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        r = s.encode(encoding, errors)
        return r
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s

def generate_smart_str(params):
    for key, value in params.iteritems():
        if value is None: continue
        if isinstance(value, (list, tuple)):
            for item in value:
                yield smart_str(key), smart_str(item)
        else:
            yield smart_str(key), smart_str(value)

def urlencode(params):
    """
    A version of Python's urllib.urlencode() function that can operate on
    unicode strings. The parameters are first case to UTF-8 encoded strings and
    then encoded as per normal.
    """
    return urllib.urlencode([i for i in generate_smart_str(params)])

def url(base_url=None, params=None, **kwargs):
    """Generate an absolute URL that's specific to this application.

    The URL function takes a string (base_url) and, appends the
    SCRIPT_NAME and adds parameters for all of the
    parameters passed into the params dict.

    For backwards compatibility you can also pass in keyword parameters.

    """
    #remove in 2.2
    if base_url is None:
        base_url = '/'
    if params is None:
        params = {}

    #First we handle the possibility that the user passed in params
    if base_url and isinstance(base_url, basestring):
        #remove in 2.2
        if kwargs.keys():
            warn('Passing in keyword arguments as url components is deprecated.'
                ' Please pass arguments as a dictionary to the params argument.',
                DeprecationWarning, stacklevel=2)
            params = params.copy()
            params.update(kwargs)

    elif hasattr(base_url, '__iter__'):
        base_url = '/'.join(base_url)
    if base_url.startswith('/'):
        base_url = tg.request.environ['SCRIPT_NAME'] + base_url
    if params:
        return '?'.join((base_url, urlencode(params)))
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

def redirect(*args, **kwargs):
    """Generate an HTTP redirect.

    The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the
    second request.
    """

    new_url = url(*args, **kwargs)
    found = HTTPFound(location=new_url).exception
    raise found

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
        raise status_map[304]().exception

def abort(status_code=None, detail="", headers=None, comment=None):
    """Aborts the request immediately by returning an HTTP exception

    In the event that the status_code is a 300 series error, the detail
    attribute will be used as the Location header should one not be
    specified in the headers attribute.

    """
    exc = status_map[status_code](detail=detail, headers=headers,
                                  comment=comment)
    raise exc.exception


def use_wsgi_app(wsgi_app):
    return wsgi_app(tg.request.environ, tg.request.start_response)


# Idea stolen from Pylons
def pylons_formencode_gettext(value):
    from tg.i18n import ugettext as tg_gettext
    from gettext import NullTranslations

    trans = tg_gettext(value)

    # Translation failed, try formencode
    if trans == value:

        try:
            fetrans = tg.tmpl_context.formencode_translation
        except AttributeError, attrerror:
            # the translator was not set in the Pylons context
            # we are certainly in the test framework
            # let's make sure won't return something that is ok with the caller
            fetrans = NullTranslations()

        if not fetrans:
            fetrans = NullTranslations()

        trans = fetrans.ugettext(value)

    return trans

__all__ = [
    "url", "lurl", "redirect", "etag_cache", "abort"
    ]
