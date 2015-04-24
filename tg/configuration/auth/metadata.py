from zope.interface import implementer
from repoze.who.interfaces import IMetadataProvider, IAuthenticator
from repoze.who.api import Identity

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


@implementer(IMetadataProvider)
class _AuthMetadataProvider(object):
    """
    repoze.who metadata provider to load groups and permissions data for
    the current user. This uses a :class:`TGAuthMetadata` to fetch
    the groups and permissions.
    """

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
            environ['repoze.what.credentials'] = Identity()
        environ['repoze.what.credentials'].update(identity)
        environ['repoze.what.credentials']['repoze.what.userid'] = userid


@implementer(IAuthenticator)
class _AuthMetadataAuthenticator(object):
    def __init__(self, tgmdprovider, using_password):
        self.tgmdprovider = tgmdprovider
        self.using_password = using_password

    # IAuthenticator
    def authenticate(self, environ, identity):
        if self.using_password and not ('login' in identity and 'password' in identity):
            return None
        return self.tgmdprovider.authenticate(environ, identity)


def create_default_authenticator(using_password=True, translations=None,
                                 user_class=None, dbsession=None,
                                 **kept_params):
    auth = _AuthMetadataAuthenticator(kept_params['authmetadata'], using_password)
    return kept_params, auth
