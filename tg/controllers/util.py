# -*- coding: utf-8 -*-
"""Helper functions for controller operation.

URL definition and browser redirection are defined here.

"""
import re
from webob.exc import status_map

import tg

from tg._compat import string_type, url_encode, unicode_text, bytes_
from tg.exceptions import HTTPFound
from tg.request_local import request, response, Response
from tg.configuration.utils import TGConfigError


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


def abort(status_code=None, detail="", headers=None, comment=None,
          passthrough=False, error_handler=False):
    """Aborts the request immediately by returning an HTTP exception

    In the event that the status_code is a 300 series error, the detail
    attribute will be used as the Location header should one not be
    specified in the headers attribute.

    **passthrough**
        When ``True`` instead of displaying the custom error
        document for errors or the authentication page for
        failed authorizations the response will just pass
        through as is.

        Set to ``"json"`` to send out the response body in
        JSON format.

    **error_handler**
        When ``True`` instead of immediately abort the request
        it will create a callable that can be used as ``@validate``
        error_handler.

        A common case is ``abort(404, error_handler=True)`` as
        ``error_handler`` for validation that retrieves objects
        from database::

            from formencode.validators import Wrapper

            @validate({'team': Wrapper(to_python=lambda value:
                                        Group.query.find({'group_name': value}).one())},
                      error_handler=abort(404, error_handler=True))
            def view_team(self, team):
                return dict(team=team)

    """
    exc = status_map[status_code](detail=detail, headers=headers,
                                  comment=comment)

    if passthrough == 'json':
        exc.content_type = 'application/json'
        exc.charset = 'utf-8'
        exc.body = tg.json_encode(dict(status=status_code,
                                       detail=str(exc))).encode('utf-8')

    def _abortion(*args, **kwargs):
        if passthrough:
            tg.request.environ['tg.status_code_redirect'] = False
            tg.request.environ['tg.skip_auth_challenge'] = False
        raise exc

    if error_handler is False:
        return _abortion()
    else:
        return _abortion


def use_wsgi_app(wsgi_app):
    return tg.request.get_response(wsgi_app)


def auth_force_login(user_name):
    """Forces user login if authentication is enabled.

    As TurboGears identifies users by ``user_name`` the passed parameter should
    be anything your application declares being the ``user_name`` field in models.

    """
    req = request._current_obj()
    resp = response._current_obj()

    api = req.environ.get('repoze.who.api')
    if api:
        authentication_plugins = req.environ['repoze.who.plugins']
        try:
            identifier = authentication_plugins['main_identifier']
        except KeyError:
            raise TGConfigError('No repoze.who plugin registered as "main_identifier"')

        resp.headers.extend(api.remember({
            'repoze.who.userid': user_name,
            'identifier': identifier
        }))


def auth_force_logout():
    """Forces user logout if authentication is enabled."""
    req = request._current_obj()
    resp = response._current_obj()

    api = req.environ.get('repoze.who.api')
    if api:
        resp.headers.extend(api.forget())


def validation_errors_response(*args, **kwargs):
    """Returns a :class:`.Response` object with validation errors.

    The response will be created with a *412 Precondition Failed*
    status code and errors are reported in JSON format as response body.

    Typical usage is as ``error_handler`` for JSON based api::

        @expose('json')
        @validate({'display_name': validators.NotEmpty(),
                   'group_name': validators.NotEmpty()},
                  error_handler=validation_errors_response)
        def post(self, **params):
            group = Group(**params)
            return dict(group=group)

    """
    req = request._current_obj()
    errors = dict(((str(key), str(error)) for key, error in req.validation.errors.items()))
    values = req.validation['values']
    try:
        return Response(status=412, json_body={'errors': errors,
                                               'values': values})
    except TypeError:
        # values cannot be encoded to JSON, this might happen after
        # validation passed and validators converted them to complex objects.
        # In this case use request params, instead of controller params.
        return Response(status=412, json_body={'errors': errors,
                                               'values': req.args_params})

__all__ = ['url', 'lurl', 'redirect', 'etag_cache', 'abort', 'auth_force_logout',
           'auth_force_login', 'validation_errors_response', 'use_wsgi_app']
