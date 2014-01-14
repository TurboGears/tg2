from tg.controllers.util import _build_url

try:
    from urlparse import urlparse, urlunparse, parse_qs
except ImportError: #pragma: no cover
    from urllib.parse import urlparse, urlunparse, parse_qs

try:
    from urllib import urlencode
except ImportError: #pragma: no cover
    from urllib.parse import urlencode

from webob import Request
from webob.exc import HTTPFound, HTTPUnauthorized
from zope.interface import implementer

from repoze.who.interfaces import IChallenger, IIdentifier

@implementer(IChallenger, IIdentifier)
class FastFormPlugin(object):
    """
    Simplified and faster version of the repoze.who.friendlyforms
    FriendlyForm plugin. The FastForm version works only with UTF-8
    content which is the default for new WebOb versions.
    """
    classifications = {
        IIdentifier: ["browser"],
        IChallenger: ["browser"],
        }

    def __init__(self, login_form_url, login_handler_path, post_login_url,
                 logout_handler_path, post_logout_url, rememberer_name,
                 login_counter_name=None):
        """
        :param login_form_url: The URL/path where the login form is located.
        :type login_form_url: str
        :param login_handler_path: The URL/path where the login form is
            submitted to (where it is processed by this plugin).
        :type login_handler_path: str
        :param post_login_url: The URL/path where the user should be redirected
            to after login (even if wrong credentials were provided).
        :type post_login_url: str
        :param logout_handler_path: The URL/path where the user is logged out.
        :type logout_handler_path: str
        :param post_logout_url: The URL/path where the user should be
            redirected to after logout.
        :type post_logout_url: str
        :param rememberer_name: The name of the repoze.who identifier which
            acts as rememberer.
        :type rememberer_name: str
        """
        self.login_form_url = login_form_url
        self.login_handler_path = login_handler_path
        self.post_login_url = post_login_url
        self.logout_handler_path = logout_handler_path
        self.post_logout_url = post_logout_url
        self.rememberer_name = rememberer_name

        if not login_counter_name:
            login_counter_name = '__logins'
        self.login_counter_name = login_counter_name

    # IIdentifier
    def identify(self, environ):
        path_info = environ['PATH_INFO']

        if path_info == self.login_handler_path:
            query = self._get_form_data(environ)

            try:
                credentials = {'login': query['login'],
                               'password': query['password'],
                               'max_age':query.get('remember')}
            except KeyError:
                credentials = None

            params = {}
            if 'came_from' in query:
                params['came_from'] = query['came_from']
            if self.login_counter_name is not None and self.login_counter_name in query:
                params[self.login_counter_name] = query[self.login_counter_name]

            destination = _build_url(environ, self.post_login_url, params=params)
            environ['repoze.who.application'] = HTTPFound(location=destination)
            return credentials

        elif path_info == self.logout_handler_path:
            query = self._get_form_data(environ)
            came_from = query.get('came_from')
            if came_from is None:
                came_from = _build_url(environ, '/')

            # set in environ for self.challenge() to find later
            environ['came_from'] = came_from
            environ['repoze.who.application'] = HTTPUnauthorized()

        elif path_info in (self.login_form_url, self.post_login_url):
            query = self._get_form_data(environ)
            environ['repoze.who.logins'] = 0

            if self.login_counter_name is not None and self.login_counter_name in query:
                environ['repoze.who.logins'] = int(query[self.login_counter_name])
                del query[self.login_counter_name]
                environ['QUERY_STRING'] = urlencode(query, doseq=True)

        return None

    # IChallenger
    def challenge(self, environ, status, app_headers, forget_headers):
        path_info = environ['PATH_INFO']

        # Configuring the headers to be set:
        cookies = [(h,v) for (h,v) in app_headers if h.lower() == 'set-cookie']
        headers = forget_headers + cookies

        if path_info == self.logout_handler_path:
            params = {}
            if 'came_from' in environ:
                params.update({'came_from':environ['came_from']})
            destination = _build_url(environ, self.post_logout_url, params=params)

        else:
            came_from_params = parse_qs(environ.get('QUERY_STRING', ''))
            params = {'came_from': _build_url(environ, path_info, came_from_params)}
            destination = _build_url(environ, self.login_form_url, params=params)

        return HTTPFound(location=destination, headers=headers)

    # IIdentifier
    def remember(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.remember(environ, identity)

    # IIdentifier
    def forget(self, environ, identity):
        rememberer = self._get_rememberer(environ)
        return rememberer.forget(environ, identity)

    def _get_rememberer(self, environ):
        rememberer = environ['repoze.who.plugins'][self.rememberer_name]
        return rememberer

    def _get_form_data(self, environ):
        request = Request(environ)
        query = dict(request.GET)
        query.update(request.POST)
        return query

    def __repr__(self):
        return '<%s:%s %s>' % (self.__class__.__name__, self.login_handler_path, id(self))
