from zope.interface import implementer
from repoze.who.interfaces import IAuthenticator


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


def create_default_authenticator(authmetadata,
                                 using_password=True, translations=None,
                                 user_class=None, dbsession=None,
                                 **kept_params):
    auth = _AuthMetadataAuthenticator(authmetadata, using_password)
    return kept_params, auth
