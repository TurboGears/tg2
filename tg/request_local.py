import base64
import binascii
import hmac
import pickle
import urllib.parse
from hashlib import sha1

from webob import Request as WebObRequest
from webob import Response as WebObResponse
from webob.request import PATH_SAFE

from .caching import cached_property
from .support.objectproxy import TurboGearsObjectProxy
from .support.registry import DispatchingConfig, StackedObjectProxy


class Request(WebObRequest):
    """WebOb Request subclass

    The WebOb :class:`webob.Request` has no charset, or other defaults. This subclass
    adds defaults, along with several methods for backwards
    compatibility with paste.wsgiwrappers.WSGIRequest.

    """

    def _fast_setattr(self, name, value):
        object.__setattr__(self, name, value)

    def languages_best_match(self, fallback=None):
        al = self.accept_language
        try:
            items = [i for i, q in sorted(al._parsed, key=lambda iq: -iq[1])]
        except (AttributeError, TypeError):
            # NilAccept has no _parsed, here for test units
            items = []

        if fallback:
            items.append(fallback)

        return items

    @cached_property
    def dispatch_state(self):
        """Details and info about dispatcher that handled this request."""
        return self._dispatch_state

    @cached_property
    def controller_url(self):
        """Url of the current controller."""
        state = self._dispatch_state
        return "/".join(state.path[: -len(state.remainder)])

    @cached_property
    def plain_languages(self):
        """Return the list of browser preferred languages"""
        return self.languages_best_match()

    @cached_property
    def languages(self):
        """Return the list of browser preferred languages ensuring that ``i18n.lang`` is listed."""
        return self.languages_best_match(self._language)

    @property
    def response_type(self):
        """Expected response content type when URL Extensions are enabled.

        In case URL Request Extension is enabled this will be the content type
        of the expected response. ``disable_request_extensions`` drives
        this is enabled or not.
        """
        return self._response_type

    @property
    def response_ext(self):
        """URL extension when URL Extensions are enabled.

        In case URL Request Extension is enabled this will be the extension of the url.
        ``disable_request_extensions`` drives this is enabled or not.
        """
        return self._response_ext

    def match_accept(self, mimetypes):
        return self.accept.best_match(mimetypes)

    def signed_cookie(self, name, secret):
        """Extract a signed cookie of ``name`` from the request

        The cookie is expected to have been created with
        ``Response.signed_cookie``, and the ``secret`` should be the
        same as the one used to sign it.

        Any failure in the signature of the data will result in None
        being returned.

        """
        cookie = self.cookies.get(name)
        if not cookie:
            return

        secret = secret.encode("ascii")
        try:
            # Keep base64.decodestring for backward compatibility.
            # In the past Response.signed_cookie used base64.encodestring which could
            # lead to multiple lines in the encoded text. That's in theory unsupported
            # as cookies can't have newlines, but we still want to be able to decode it.
            try:
                base64decode = base64.decodebytes
            except AttributeError:  # pragma: no cover
                base64decode = base64.decodestring
            sig, pickled = cookie[:40], base64decode(cookie[40:].encode("ascii"))
        except binascii.Error:  # pragma: no cover
            # Badly formed data can make base64 die
            return

        if hmac.new(secret, pickled, sha1).hexdigest() == sig:
            return pickle.loads(pickled)

    @cached_property
    def args_params(self):
        """Arguments used for dispatching the request.

        This mixes GET and POST arguments.
        """
        # This was: dict(((str(n), v) for n,v in self.params.mixed().items()))
        # so that keys were all strings making possible to use them as arguments.
        # Now it seems that all keys are always strings, did WebOb change behavior?
        return self.params.mixed()

    @property
    def quoted_path_info(self):
        """PATH used for dispatching the request."""
        bpath = str(self.path_info).encode(self.url_encoding)
        return urllib.parse.quote(bpath, PATH_SAFE)

    def disable_error_pages(self):
        """Disable custom error pages for the current request.

        This will forward your response as is bypassing the :class:`.ErrorPageApplicationWrapper`
        """
        self.environ["tg.status_code_redirect"] = False

    def disable_auth_challenger(self):
        """Disable authentication challenger for current request.

        This will forward your response as is in case of 401 bypassing any
        repoze.who challenger.
        """
        self.environ["tg.skip_auth_challenge"] = True


class Response(WebObResponse):
    """WebOb Response subclass"""

    _DEFAULT_RESPONSE_OPTIONS = dict(
        content_type="text/html",
        charset="utf-8",
        headers={
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Content-Type": None,
            "Content-Length": "0",
        },
    )

    content = WebObResponse.body

    def wsgi_response(self):
        return self.status, self.headers, self.body

    def signed_cookie(self, name, data, secret, **kwargs):
        """Save a signed cookie with ``secret`` signature

        Saves a signed cookie of the pickled data. All other keyword
        arguments that ``WebOb.set_cookie`` accepts are usable and
        passed to the WebOb set_cookie method after creating the signed
        cookie value.

        """
        secret = secret.encode("ascii")

        pickled = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
        sig = hmac.new(secret, pickled, sha1).hexdigest().encode("ascii")
        cookie_value = sig + base64.b64encode(pickled)
        self.set_cookie(name, cookie_value, **kwargs)

    @property
    def content_type(self):
        return WebObResponse.content_type.__get__(self, type(self))

    @content_type.setter
    def content_type(self, value):
        WebObResponse.content_type.__set__(self, value)

    @content_type.deleter
    def content_type(self):
        WebObResponse.content_type.__delete__(self)


config = DispatchingConfig()
context = StackedObjectProxy(name="context")


class TurboGearsContextMember(TurboGearsObjectProxy):
    """Member of the TurboGears request context.

    Provides access to turbogears context members
    like request, response, template context and so on

    """

    def __init__(self, name):
        self.__dict__["name"] = name

    def _current_obj(self):
        return getattr(context, self.name)


request = TurboGearsContextMember(name="request")
app_globals = TurboGearsContextMember(name="app_globals")
cache = TurboGearsContextMember(name="cache")
response = TurboGearsContextMember(name="response")
session = TurboGearsContextMember(name="session")
tmpl_context = TurboGearsContextMember(name="tmpl_context")
url = TurboGearsContextMember(name="url")
translator = TurboGearsContextMember(name="translator")

__all__ = [
    "app_globals",
    "request",
    "response",
    "tmpl_context",
    "session",
    "cache",
    "translator",
    "url",
    "config",
]
