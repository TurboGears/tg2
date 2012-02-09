# -*- coding: utf-8 -*-
"""Helper functions for controller operation.

URL definition and browser redirection are defined here.

"""

import urllib
from warnings import warn


import pylons

from tg.exceptions import HTTPFound


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.

    This function was borrowed from Django.

    """
    if strings_only and (s is None or isinstance(s, int)):
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
        if value is None:
            continue
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
    # remove in 2.2
    if base_url is None:
        base_url = '/'
    if params is None:
        params = {}

    # First we handle the possibility that the user passed in params
    if base_url and isinstance(base_url, basestring):
        # remove in 2.2
        if kwargs.keys():
            warn('Passing in keyword arguments as URL components to url()'
                ' is deprecated. Please pass arguments as a dictionary'
                ' to the params argument.', DeprecationWarning, stacklevel=2)
            params = params.copy()
            params.update(kwargs)

    elif hasattr(base_url, '__iter__'):
        base_url = '/'.join(base_url)
    if base_url.startswith('/'):
        base_url = pylons.request.environ['SCRIPT_NAME'] + base_url
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


def use_wsgi_app(wsgi_app):
    return wsgi_app(pylons.request.environ, pylons.request.start_response)


# Idea stolen from Pylons
def pylons_formencode_gettext(value):
    from pylons.i18n import ugettext as pylons_gettext
    from gettext import NullTranslations

    trans = pylons_gettext(value)

    # Translation failed, try formencode
    if trans == value:

        try:
            fetrans = pylons.tmpl_context.formencode_translation
        except AttributeError:
            # the translator was not set in the Pylons context
            # we are certainly in the test framework
            # let's make sure won't return something that is ok with the caller
            fetrans = NullTranslations()

        if not fetrans:
            fetrans = NullTranslations()

        trans = fetrans.ugettext(value)

    return trans

__all__ = ['url', 'lurl', 'redirect', 'etag_cache']
