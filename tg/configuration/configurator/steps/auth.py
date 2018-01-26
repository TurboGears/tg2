# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging
import warnings

from ..base import (ConfigurationStep, AppReadyConfigurationAction, BeforeConfigConfigurationAction)
from ...utils import TGConfigError, get_partial_dict
from ....support.converters import asbool, aslogger


class SimpleAuthenticationConfigurationStep(ConfigurationStep):
    """
    """
    id = "sa_auth"
    SUPPORTED_AUTH_BACKENDS = ("ming", "sqlalchemy")

    def get_defaults(self):
        return {
            'auth_backend': None,
            'skip_authentication': False,
            'sa_auth.log_stream': logging.getLogger('auth'),
            'sa_auth.form_plugin': None
        }

    def get_coercion(self):

        return {
            'skip_authentication': asbool,
            'sa_auth.log_stream': aslogger
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure),
            AppReadyConfigurationAction(self._add_middleware),
        )

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('Simple Authentication only works on an ApplicationConfigurator')

        from ....appwrappers.identity import IdentityApplicationWrapper
        configurator.register_application_wrapper(IdentityApplicationWrapper, after=True)

    def _configure(self, conf, app):
        if conf['auth_backend'] not in self.SUPPORTED_AUTH_BACKENDS:
            return

        if not conf['skip_authentication'] and 'sa_auth.cookie_secret' not in conf:
            raise TGConfigError("You must provide a value for authentication cookies secret. "
                                "Make sure that you have an 'sa_auth.cookie_secret' config value.")

    def _add_middleware(self, conf, app):
        """
        Configure authentication and authorization.
        """
        # Start with the current configured authentication options.
        # Depending on the auth backend a new auth_args dictionary
        # can replace this one later on.
        if conf['auth_backend'] not in self.SUPPORTED_AUTH_BACKENDS:
            return app

        auth_backend = conf['auth_backend']
        auth_args = get_partial_dict('sa_auth', conf)

        # Removing keywords not used by repoze.who:
        auth_args.pop('password_encryption_method', None)

        # Removing authmetadata as is not used by repoze.who:
        tgauthmetadata = auth_args.pop('authmetadata', None)

        try:
            pos = auth_args['authenticators'].index(('default', None))
        except KeyError:
            # Didn't specify authenticators, setup default one
            pos = None
        except ValueError:
            # Specified authenticators and default is not in there
            # so we want to skip default TG auth configuration.
            pos = -1

        if pos is None or pos >= 0:
            if getattr(tgauthmetadata, 'authenticate', None) is not None:
                from tg.configuration.auth import create_default_authenticator
                auth_args, tgauth = create_default_authenticator(tgauthmetadata, **auth_args)
                authenticator = ('tgappauth', tgauth)
            elif auth_backend == "sqlalchemy":
                warnings.warn('sqlauth is deprecated, you should add authenticate method '
                              'to your authmetadata instance in app_cfg', DeprecationWarning, 2)
                from tg.configuration.sqla.auth import create_default_authenticator
                auth_args, sqlauth = create_default_authenticator(**auth_args)
                authenticator = ('sqlauth', sqlauth)
            elif auth_backend == "ming":
                warnings.warn('mingauth is deprecated, you should add authenticate method '
                              'to your authmetadata instance in app_cfg', DeprecationWarning, 2)
                from tg.configuration.mongo.auth import create_default_authenticator
                auth_args, mingauth = create_default_authenticator(**auth_args)
                authenticator = ('mingauth', mingauth)
            else:
                authenticator = None

            if authenticator is not None:
                if pos is None:
                    auth_args['authenticators'] = [authenticator]
                else:
                    # We make a copy so that we don't modify the original one.
                    auth_args['authenticators'] = auth_args['authenticators']
                    auth_args['authenticators'][pos] = authenticator

        from tg.configuration.auth import setup_auth
        app = setup_auth(app, skip_authentication=conf['skip_authentication'], **auth_args)
        return app
