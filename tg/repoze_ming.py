from zope.interface import implements
from repoze.who.interfaces import IAuthenticator, IMetadataProvider
from repoze.who.plugins.friendlyform import FriendlyFormPlugin
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.middleware import PluggableAuthenticationMiddleware

class MingAuthenticatorPlugin(object):
    implements(IAuthenticator)

    def __init__(self, user_class):
        self.user_class = user_class

    # IAuthenticator
    def authenticate(self, environ, identity):
        if not ('login' in identity and 'password' in identity):
            return None

        user = self.user_class.query.get(user_name=identity.get('login', None))
        if user:
            if user.validate_password(identity.get('password', None)):
                return identity['login']

class MingUserMDPlugin(object):
    implements(IMetadataProvider)

    def __init__(self, user_class):
        self.user_class = user_class

    def add_metadata(self, environ, identity):
        identity['user'] = self.user_class.query.get(user_name=identity['repoze.who.userid'])
        identity['groups'] = identity['user'].groups

        if 'repoze.what.credentials' not in environ:
            environ['repoze.what.credentials'] = {}

        environ['repoze.what.credentials']['groups'] = identity['groups']
        environ['repoze.what.credentials']['repoze.what.userid'] = identity['repoze.who.userid']

def setup_ming_auth(app, skip_authentication, **auth_args):
    cookie_secret = auth_args.get('cookie_secret', 'secret')
    cookie_name = auth_args.get('cookie_name', 'authtkt')

    form_plugin = FriendlyFormPlugin(auth_args.get('login_url', '/login'),
                                     auth_args.get('login_handler', '/login_handler'),
                                     auth_args['post_login_url'],
                                     auth_args.get('logout_handler', '/logout_handler'),
                                     auth_args['post_logout_url'],
                                     login_counter_name=auth_args.get('login_counter_name'),
                                     rememberer_name='cookie')

    challengers = [('form', form_plugin)]

    auth = MingAuthenticatorPlugin(user_class=auth_args['user_class'])
    authenticators = [('mingauth', auth)]

    cookie = AuthTktCookiePlugin(cookie_secret, cookie_name)
    identifiers = [('cookie', cookie), ('form', form_plugin)]

    provider = MingUserMDPlugin(user_class=auth_args['user_class'])
    mdproviders = [('ming_user_md', provider)]

    from repoze.who.classifiers import default_request_classifier
    from repoze.who.classifiers import default_challenge_decider

    app = PluggableAuthenticationMiddleware(
        app,
        identifiers=identifiers,
        authenticators=authenticators,
        challengers=challengers,
        mdproviders=mdproviders,
        classifier=default_request_classifier,
        challenge_decider=default_challenge_decider)

    return app