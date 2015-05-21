import logging
from .base import ApplicationWrapper
from ..configuration.utils import coerce_config
from ..support.converters import asbool

log = logging.getLogger(__name__)


class IdentityApplicationWrapper(ApplicationWrapper):
    """Provides user identity when authentication is enabled.

    The repoze.who provided identity takes precedence over the identity
    provided by IdentityApplicationWrapper if available.

    Supported options which can be provided by config are:
        - ``sa_auth.authmetadata``: The TGAuthMetadata object that should be used to retrieve identity metadata.
        - ``identity.enabled``: Enable the Identity Application Wrapper. By default enabled if authmetadata available.
        - ``identity.allow_missing_user``: Whenever the identity should be discarded or not when the authmetadata is unable to find an user.

    """
    def __init__(self, handler, config):
        super(IdentityApplicationWrapper, self).__init__(handler, config)

        options = {
            'enabled': True,
            'allow_missing_user': True,
            'authmetadata': config.get('sa_auth',  {}).get('authmetadata'),
        }
        options.update(coerce_config(config, 'identity.',  {
            'enabled': asbool,
            'allow_missing_user': asbool
        }))

        self.enabled = options['enabled'] and options['authmetadata'] is not None
        self.options = options
        self.tgmdprovider = options['authmetadata']
        log.debug('Identity enabled: %s -> %s', self.enabled, self.options)

    @property
    def injected(self):
        return self.enabled

    def __call__(self, controller, environ, context):
        identity = environ.get('repoze.who.identity')
        if identity is None:
            context.request.identity = None
            return self.next_handler(controller, environ, context)

        req_identity = {}

        # Get the userid retrieved by repoze.who Authenticator
        userid = identity['repoze.who.userid']
        if userid is not None:
            # Finding the user, groups and permissions:
            identity['user'] = identity_user = self.tgmdprovider.get_user(identity, userid)

            if identity_user:
                identity['groups'] = self.tgmdprovider.get_groups(identity, userid)
                identity['permissions'] = self.tgmdprovider.get_permissions(identity, userid)
            else:
                identity['groups'] = identity['permissions'] = []

            req_identity = Identity()
            req_identity.update(identity)
            req_identity['repoze.what.userid'] = userid

            if req_identity.get('user') is None and not self.options['allow_missing_user']:
                req_identity = {}

        # Add identity to request with repoze.who/what compatibility
        context.request.identity = req_identity
        environ['repoze.who.identity'] = req_identity
        environ['repoze.what.credentials'] = req_identity

        return self.next_handler(controller, environ, context)


class Identity(dict):
    """dict subclass: prevent members from being rendered during print.

    Took as is from repoze.who.
    """
    def __repr__(self):
        return '<TurboGears Identity (hidden, dict-like) at %s>' % id(self)
    __str__ = __repr__