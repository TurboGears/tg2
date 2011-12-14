import hmac, base64
import binascii
from paste.registry import StackedObjectProxy
from paste.config import DispatchingConfig

try:
    import cPickle as pickle
except ImportError:
    import pickle

try:
    from hashlib import sha1
except ImportError:
    import sha as sha1

from webob import Request as WebObRequest
from webob import Response as WebObResponse

class Request(WebObRequest):
    """WebOb Request subclass

    The WebOb :class:`webob.Request` has no charset, or other defaults. This subclass
    adds defaults, along with several methods for backwards
    compatibility with paste.wsgiwrappers.WSGIRequest.

    """
    def determine_browser_charset(self):
        """Legacy method to return the
        :attr:`webob.Request.accept_charset`"""
        return self.accept_charset

    def languages_best_match(self, fallback=None):
        # And we now have the old best_matches code that webob ditched!
        al = self.accept_language
        if hasattr(al, 'best_matches'): # webob<1.2
            items = al.best_matches(fallback)
        else:
            items = [i for i, q in sorted(al._parsed, key=lambda iq: -iq[1])]
            if fallback:
                for index, item in enumerate(items):
                    if al._match(item, self.language):
                        items[index:] = [self.language]
                        break
                else:
                    items.append(self.language)
        return items

    @property
    def languages(self):
        return self.languages_best_match(self.language)

    def match_accept(self, mimetypes):
        return self.accept.first_match(mimetypes)

    def signed_cookie(self, name, secret):
        """Extract a signed cookie of ``name`` from the request

        The cookie is expected to have been created with
        ``Response.signed_cookie``, and the ``secret`` should be the
        same as the one used to sign it.

        Any failure in the signature of the data will result in None
        being returned.

        """
        cookie = self.str_cookies.get(name)
        if not cookie:
            return
        try:
            sig, pickled = cookie[:40], base64.decodestring(cookie[40:])
        except binascii.Error:
            # Badly formed data can make base64 die
            return
        if hmac.new(secret, pickled, sha1).hexdigest() == sig:
            return pickle.loads(pickled)

    @property
    def str_cookies(self):
        if hasattr(super(Request, self), 'str_cookies'):
            return super(Request, self).str_cookies
        
        return self.cookies

    @property
    def args_params(self):
        if hasattr(super(Request, self), 'str_params'):
            return super(Request, self).params.mixed()
        
        if not hasattr(self, '_args_params_cache'):
            self._args_params_cache = dict([(str(n), v) for n,v in self.params.mixed().iteritems()])
        return self._args_params_cache

class Response(WebObResponse):
    """WebOb Response subclass

    The WebOb Response has no default content type, or error defaults.
    This subclass adds defaults, along with several methods for
    backwards compatibility with paste.wsgiwrappers.WSGIResponse.

    """
    content = WebObResponse.body

    def determine_charset(self):
        return self.charset

    def has_header(self, header):
        return header in self.headers

    def get_content(self):
        return self.body

    def write(self, content):
        self.body_file.write(content)

    def wsgi_response(self):
        return self.status, self.headers, self.body

    def signed_cookie(self, name, data, secret=None, **kwargs):
        """Save a signed cookie with ``secret`` signature

        Saves a signed cookie of the pickled data. All other keyword
        arguments that ``WebOb.set_cookie`` accepts are usable and
        passed to the WebOb set_cookie method after creating the signed
        cookie value.

        """
        pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        sig = hmac.new(secret, pickled, sha1).hexdigest()
        self.set_cookie(name, sig + base64.encodestring(pickled), **kwargs)

config = DispatchingConfig()
app_globals = StackedObjectProxy(name="app_globals")
cache = StackedObjectProxy(name="cache")
request = StackedObjectProxy(name="request")
response = StackedObjectProxy(name="response")
session = StackedObjectProxy(name="session")
tmpl_context = StackedObjectProxy(name="tmpl_context or C")
url = StackedObjectProxy(name="url")
translator = StackedObjectProxy(name="translator")

__all__ = ['app_globals', 'request', 'response', 'tmpl_context', 'session', 'cache', 'translator', 'url', 'config']