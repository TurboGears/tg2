import hmac, base64, urllib, binascii, re
from paste.registry import StackedObjectProxy
from paste.config import DispatchingConfig
from tg.caching import cached_property

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
    def controller_state(self):
        return self._controller_state

    @property
    def fast_path(self):
        s = self.path_info
        if not _must_quote.search(s):
            return s
        return ''.join(map(_faster_safe.get, s))

    @cached_property
    def plain_languages(self):
        return self.languages_best_match()

    @property
    def languages(self):
        return self.languages_best_match(self._language)

    @property
    def language(self):
        return self._language

    @language.setter
    def language(self, value):
        self._language = value

    @property
    def response_type(self):
        return self._response_type

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

    @cached_property
    def args_params(self):
        if old_webob:
            return self.params.mixed()
        else:
            return dict([(str(n), v) for n,v in self.params.mixed().iteritems()])

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
context = StackedObjectProxy(name="context")

class TurboGearsContextMember(object):
    """Member of the TurboGears request context.

    Mostly inspired by StackedObjectProxy it
    provides access to turbogears context members
    like request, response, template context and so on

    """

    def __init__(self, name):
        self.__dict__['name'] = name

    def _current_obj(self):
        return getattr(context, self.name)

    def __dir__(self):
        dir_list = dir(self.__class__) + self.__dict__.keys()
        try:
            dir_list.extend(dir(self._current_obj()))
        except TypeError:
            pass
        dir_list.sort()
        return dir_list

    def __getattr__(self, attr):
        return getattr(self._current_obj(), attr)

    def __setattr__(self, attr, value):
        setattr(self._current_obj(), attr, value)

    def __delattr__(self, name):
        delattr(self._current_obj(), name)

    def __getitem__(self, key):
        return self._current_obj()[key]

    def __setitem__(self, key, value):
        self._current_obj()[key] = value

    def __delitem__(self, key):
        del self._current_obj()[key]

    def __call__(self, *args, **kw):
        return self._current_obj()(*args, **kw)

    def __repr__(self):
        try:
            return repr(self._current_obj())
        except (TypeError, AttributeError):
            return '<%s.%s object at 0x%x>' % (self.__class__.__module__,
                                               self.__class__.__name__,
                                               id(self))

    def __iter__(self):
        return iter(self._current_obj())

    def __len__(self):
        return len(self._current_obj())

    def __contains__(self, key):
        return key in self._current_obj()

    def __nonzero__(self):
        return bool(self._current_obj())


request = TurboGearsContextMember(name="request")
app_globals = TurboGearsContextMember(name="app_globals")
cache = TurboGearsContextMember(name="cache")
response = TurboGearsContextMember(name="response")
session = TurboGearsContextMember(name="session")
tmpl_context = TurboGearsContextMember(name="tmpl_context")
url = TurboGearsContextMember(name="url")
translator = TurboGearsContextMember(name="translator")

__all__ = ['app_globals', 'request', 'response', 'tmpl_context', 'session', 'cache', 'translator', 'url', 'config']