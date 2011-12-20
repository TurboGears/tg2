import hmac, base64, urllib, binascii, re
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
from webob.request import PATH_SAFE
from webob import Response as WebObResponse

#Precalc url quoting for fast_path property
always_safe = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
               'abcdefghijklmnopqrstuvwxyz'
               '0123456789' '_.-')
_faster_safe_test = always_safe + PATH_SAFE
_faster_safe = dict(zip(_faster_safe_test, _faster_safe_test))
for c in [chr(i) for i in range(256)]:
    if c not in _faster_safe:
        _faster_safe[c] = '%%%02X' % ord(c)
_must_quote = re.compile(r'[^%s]' % _faster_safe_test)

try:
    WebObRequest.str_cookies
    old_webob = True
except:
    old_webob = False

class Request(WebObRequest):
    """WebOb Request subclass

    The WebOb :class:`webob.Request` has no charset, or other defaults. This subclass
    adds defaults, along with several methods for backwards
    compatibility with paste.wsgiwrappers.WSGIRequest.

    """

    def __init__(self, *args, **kw):
        super(Request, self).__init__(*args, **kw)
        self.__dict__.update({'_response_type': None,
                              '_render_custom_format':{},
                              '_override_mapping':{},
                              '_args_params_cache':None})

    def determine_browser_charset(self):
        """Legacy method to return the
        :attr:`webob.Request.accept_charset`"""
        return self.accept_charset

    def languages_best_match(self, fallback=None):
        al = self.accept_language
        if old_webob: # webob<1.2
            items = al.best_matches(fallback)
        else:
            items = [i for i, q in sorted(al._parsed, key=lambda iq: -iq[1])]
            if fallback:
                for index, item in enumerate(items):
                    if al._match(item, fallback):
                        items[index:] = [fallback]
                        break
                else:
                    items.append(fallback)
        return items

    @property
    def fast_path(self):
        s = ''.join((self.script_name, self.path_info))
        if not _must_quote.search(s):
            return s
        return ''.join(map(_faster_safe.get, s))

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
        if old_webob:
            return super(Request, self).str_cookies
        
        return self.cookies

    @property
    def args_params(self):
        if old_webob:
            return self.params.mixed()
        
        if not self._args_params_cache:
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