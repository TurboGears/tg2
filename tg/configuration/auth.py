"""
New TurboGears2 identification, authentication and authorization setup.

This aims to provide an easier way to setup auth layer in TurboGears2
and removes the dependency from repoze.what.
"""
import sys, logging, re
from paste.deploy.converters import asbool
from zope.interface import implements
from repoze.who.middleware import PluggableAuthenticationMiddleware
from repoze.who.interfaces import IMetadataProvider, IIdentifier, IAuthenticator, IChallenger
from repoze.who.classifiers import default_challenge_decider, default_request_classifier
from repoze.who.config import _LEVELS
from webob.exc import HTTPUnauthorized

class TGAuthMetadata(object):
    """
    Provides a way to lookup for user, groups and permissions
    given the current identity. This has to be specialized
    for each storage backend.

    By default it returns empty lists for groups and permissions
    and None for the user.
    """
    def get_user(self, identity, userid):
        return None

    def get_groups(self, identity, userid):
        return []

    def get_permissions(self, identity, userid):
        return []

class _AuthMetadataProvider(object):
    """
    repoze.who metadata provider to load groups and permissions data for
    the current user. This uses a :class:`TGAuthMetadata` to fetch
    the groups and permissions.
    """
    implements(IMetadataProvider)

    def __init__(self, tgmdprovider):
        self.tgmdprovider = tgmdprovider

    # IMetadataProvider
    def add_metadata(self, environ, identity):
        # Get the userid retrieved by repoze.who Authenticator
        userid = identity['repoze.who.userid']

        # Finding the user, groups and permissions:
        identity['user'] = self.tgmdprovider.get_user(identity, userid)
        if identity['user']:
            identity['groups'] = self.tgmdprovider.get_groups(identity, userid)
            identity['permissions'] = self.tgmdprovider.get_permissions(identity, userid)
        else:
            identity['groups'] = identity['permissions'] = []

        # Adding the groups and permissions to the repoze.what
        # credentials for repoze.what compatibility:
        if 'repoze.what.credentials' not in environ:
            environ['repoze.what.credentials'] = {}
        environ['repoze.what.credentials'].update(identity)
        environ['repoze.what.credentials']['repoze.what.userid'] = userid

class _AuthenticationForgerPlugin(object):
    """
    Took from repoze.who_testutil.
    This is meant for internal use only to setup tests with fake
    authentication. It is a repoze.who plugin which skips
    all challenger, authentication and identifiers and returns
    the user contained in REMOTE_USER environment key.
    Has been made internal part of TG to make
    possible to switch to repoze.who v2
    """
    implements(IIdentifier, IAuthenticator, IChallenger)
    _HTTP_STATUS_PATTERN = re.compile(r'^(?P<code>[0-9]{3}) (?P<reason>.*)$')

    def __init__(self, fake_user_key='REMOTE_USER',
                 remote_user_key='repoze.who.testutil.userid'):
        self.fake_user_key = fake_user_key
        self.remote_user_key = remote_user_key

    def identify(self, environ):
        if self.fake_user_key in environ:
            identity = {'fake-userid': environ[self.fake_user_key]}
            return identity

    def remember(self, environ, identity):
        pass

    def forget(self, environ, identity):
        pass

    def authenticate(self, environ, identity):
        if 'fake-userid' in identity:
            environ[self.remote_user_key] = identity.pop('fake-userid')
            return environ[self.remote_user_key]

    def challenge(self, environ, status, app_headers, forget_headers):
        """Return a 401 page unconditionally."""
        headers = app_headers + forget_headers
        #remove content-length header
        headers = filter(lambda h:h[0].lower() != 'content-length', headers)
        # The HTTP status code and reason may not be the default ones:
        status_parts = self._HTTP_STATUS_PATTERN.search(status)
        if status_parts:
            reason = status_parts.group('reason')
            code = int(status_parts.group('code'))
        else:
            reason = 'HTTP Unauthorized'
            code = 401
            # Building the response:
        response = HTTPUnauthorized(headers=headers)
        response.title = reason
        response.code = code
        return response


class _AuthenticationForgerMiddleware(PluggableAuthenticationMiddleware):
    def __init__(self, app, identifiers, authenticators, challengers,
                 mdproviders, classifier, challenge_decider, log_stream=None,
                 log_level=logging.INFO, remote_user_key='REMOTE_USER'):
        """
        Took from repoze.who_testutil.
        This is meant for internal use only to setup tests with fake
        authentication. Has been made internal part of TG to make
        possible to switch to repoze.who v2
        """

        self.actual_remote_user_key = remote_user_key
        forger = _AuthenticationForgerPlugin(fake_user_key=remote_user_key)
        forger = ('auth_forger', forger)
        identifiers.insert(0, forger)
        authenticators = [forger]
        challengers = [forger]

        # Calling the parent's constructor:
        init = super(_AuthenticationForgerMiddleware, self).__init__
        init(app, identifiers, authenticators, challengers, mdproviders,
            classifier, challenge_decider, log_stream, log_level,
            'repoze.who.testutil.userid')

def setup_auth(app, authmetadata,
              form_plugin=None, form_identifies=True,
              cookie_secret='secret', cookie_name='authtkt',
              login_url='/login', login_handler='/login_handler',
              post_login_url=None, logout_handler='/logout_handler',
              post_logout_url=None, login_counter_name=None,
              cookie_timeout=None, cookie_reissue_time=None,
              charset="iso-8859-1",
              **who_args):
    """
    Sets :mod:`repoze.who` up with the provided authenticators and
    options to create FriendlyFormPlugin.

    It returns a middleware that provides identification,
    authentication and authorization in a way that is compatible
    with repoze.who and repoze.what.
    """

    # If no identifiers are provided in repoze setup arguments
    # then create a default one using AuthTktCookiePlugin.
    if 'identifiers' not in who_args:
        from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
        cookie = AuthTktCookiePlugin(cookie_secret, cookie_name,
                                     timeout=cookie_timeout,
                                     reissue_time=cookie_reissue_time)
        who_args['identifiers'] = [('cookie', cookie)]
        who_args['authenticators'].insert(0, ('cookie', cookie))

    # If no form plugin is provided then create a default
    # one using the provided options.
    if form_plugin is None:
        from repoze.who.plugins.friendlyform import FriendlyFormPlugin
        form = FriendlyFormPlugin(login_url, login_handler, post_login_url,
                                  logout_handler, post_logout_url,
                                  login_counter_name=login_counter_name,
                                  rememberer_name='cookie',
                                  charset=charset)
    else:
        form = form_plugin

    if form_identifies:
        who_args['identifiers'].insert(0, ('main_identifier', form))

    # Setting the repoze.who challengers:
    if 'challengers' not in who_args:
        who_args['challengers'] = []
    who_args['challengers'].append(('form', form))

    # Including logging
    log_file = who_args.pop('log_file', None)
    if log_file is not None:
        if log_file.lower() == 'stdout':
            log_stream = sys.stdout
        elif log_file.lower() == 'stderr':
            log_stream = sys.stderr
        else:
            log_stream = open(log_file, 'wb')
        who_args['log_stream'] = log_stream

    log_level = who_args.get('log_level', None)
    if log_level is None:
        log_level = logging.INFO
    else:
        log_level = _LEVELS[log_level.lower()]
    who_args['log_level'] = log_level

    # Setting up the metadata provider for the user informations
    if 'mdproviders' not in who_args:
        who_args['mdproviders'] = []

    if authmetadata:
        authmd = _AuthMetadataProvider(authmetadata)
        who_args['mdproviders'].append(('authmd', authmd))

    # Set up default classifier
    if 'classifier' not in who_args:
        who_args['classifier'] = default_request_classifier

    # Set up default challenger decider
    if 'challenge_decider' not in who_args:
        who_args['challenge_decider'] = default_challenge_decider

    skip_authn = who_args.pop('skip_authentication', False)
    if asbool(skip_authn):
        return _AuthenticationForgerMiddleware(app, **who_args)
    else:
        return PluggableAuthenticationMiddleware(app, **who_args)
