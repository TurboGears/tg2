# -*- coding: utf-8 -*-
from __future__ import absolute_import

import logging

from ...configuration.utils import TGConfigError
from ...support.converters import asbool, aslogger
from ...util.bunch import get_partial_dict
from ..base import (
    AppReadyConfigurationAction,
    BeforeConfigConfigurationAction,
    ConfigurationComponent,
)


class SimpleAuthenticationConfigurationComponent(ConfigurationComponent):
    """Provide support for Simple Authentication.

    Simple Authentication is the standard way to handle authentication
    and authorization in TurboGears. Where every request has an associated
    User object (which might be None) and each user can be part of one or more
    Groups each having a set of Permissions.

    The simple auth is based on ``repoze.who`` and by default sets the
    required ``authenticators``, ``identifiers`` and ``metadata providers``
    for a form based login. The user, its groups and permissions are retrieved
    through the ``authmetadata`` object configured by the application.

    For most cases instead of tweaking the simple authentication options
    you probably just want to change the behaviour of ``authmetadata``
    object in your application configuration.

    Provided options:

        * ``sa_auth.enabled``: Enabled/Disable simple authentication, by default True.
        * ``skip_authentication``: Disable authentication for tests, the
          user will always be authenticated through a ``REMOTE_USER`` environ
          key which will be considered the authenticated user id when set.
        * ``sa_auth.authmetadata``: authmetadata instance to use as an authenticator.
          Can be None for no authenticator.
        * ``sa_auth.log_stream``: Provide a custom logger fo authentication.
          by default the ``auth`` logger is used.
        * ``sa_auth.identifiers``: The identifiers to use to recognise a logged user.
          By default ``('default', None)`` leads to an authentication cookie being
          used to recognise logged users.
        * ``sa_auth.form_identifies``: Whenever to add the form plugin to
          the identifiers. By default ``True``. This allows the form plugin
          to intercept requests and identify the user credentisl from the
          data submitted by the login page. If this is
          disabled, the form will be able to act as a challenger and redirect
          the user to the login page, but it won't be able to actually get the
          user_name/password from the submitted form and provide them to the
          authenticator.
        * ``sa_auth.cookie_secret``: Secret to encode the ``auth_tkt`` cookie.
          This is only required when ``('default', None)`` is listed
          in ``sa_auth.identifiers``.
        * ``sa_auth.authenticators``: List of authenticators used to authenticate
          user against the provided credentials. By default ``('default', None)`` and
          ``cookie`` are the only enabled ones. This means that user will be
          authenticated against an user name and password using authmetadata or
          will be authenticated through the presence of an authentication cookie.
        * ``sa_auth.cookie_name``: Name of the cookie used to authenticate the
          user if the cookie identifer and authenticator are enabled (by default they are).
        * ``sa_auth.login_url``: Url where the login form is displayed if
          ``sa_auth.form_plugin`` is enabled. By default ``"/login"``.
        * ``sa_auth.login_handler``: Url that should handle form submitted authentication
          requests if ``sa_auth.form_plugin`` is enabled and it is allowed to identify.
          By default it's ``"/login_handler"``.
        * ``sa_auth.logout_handler``: Url that should handle logout requests
          if ``sa_auth.form_plugin`` is enabled and it is allowed to identify.
          By default it's ``"/logout_handler"``
        * ``sa_auth.post_login_url``: Where to redirect user after a login.
          Only applied if ``sa_auth.form_plugin`` is enabled and allowed to identify.
        * ``sa_auth.post_logout_url`` Where to redirect user after a logout.
          Only applied if ``sa_auth.form_plugin`` is enabled and allowed to identify.
        * ``sa_auth.login_counter_name``: Parameter used by form login to keep track
          of login attempts if `sa_auth.form_plugin`` is enabled. By default ``__logins``.
        * ``sa_auth.form_plugin``: Provide an alternative login/logout implement
          for form based authentication.  This might make all ``form_plugin`` related
          options unusable.
        * ``sa_auth.mdproviders``: Enable some metadata providers. This are used to
          inject additional user details into the current request. By default it's
          disabled and :class:`tg.appwrappers.identity.IdentityApplicationWrapper` is
          used instead.
        * ``sa_auth.authtkt.timeout``: Timeout of the authtkt token.
        * ``sa_auth.authtkt.reissue_time``: Frequency at which the authtkt token
                                            should be refreshed.
        * ``sa_auth.authtkt.secure``: Make cookie HTTPS only and disable Javascript access.
        * ``sa_auth.authtkt.samesite``: Enable a ``SameSite=X`` option on the cookie.

    """

    id = "sa_auth"

    def get_defaults(self):
        return {
            "sa_auth.enabled": False,
            "skip_authentication": False,
            "sa_auth.log_stream": logging.getLogger("auth"),
            "sa_auth.form_plugin": None,
        }

    def get_coercion(self):
        return {
            "sa_auth.enabled": asbool,
            "skip_authentication": asbool,
            "sa_auth.log_stream": aslogger,
            "sa_auth.form_identifies": asbool,
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure),
            AppReadyConfigurationAction(self._add_middleware),
        )

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator

        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError(
                "Simple Authentication only works on an ApplicationConfigurator"
            )

        from ...appwrappers.identity import IdentityApplicationWrapper

        configurator.register_application_wrapper(
            IdentityApplicationWrapper, after=True
        )

    def _configure(self, conf, app):
        if not conf["sa_auth.enabled"]:
            return

        if not conf["skip_authentication"] and "sa_auth.cookie_secret" not in conf:
            raise TGConfigError(
                "You must provide a value for authentication cookies secret. "
                "Make sure that you have an 'sa_auth.cookie_secret' config value."
            )

    def _add_middleware(self, conf, app):
        """
        Configure authentication and authorization.
        """
        # Start with the current configured authentication options.
        # Depending on the auth backend a new auth_args dictionary
        # can replace this one later on.
        if not conf["sa_auth.enabled"]:
            return app

        auth_args = get_partial_dict("sa_auth", conf)

        # Removing keywords not used by repoze.who:
        auth_args.pop("enabled", None)
        auth_args.pop("password_encryption_method", None)

        # Removing authmetadata as is not used by repoze.who:
        tgauthmetadata = auth_args.pop("authmetadata", None)

        try:
            pos = auth_args["authenticators"].index(("default", None))
        except KeyError:
            # Didn't specify authenticators, setup default one
            pos = None
        except ValueError:
            # Specified authenticators and default is not in there
            # so we want to skip default TG auth configuration.
            pos = -1

        if pos is None or pos >= 0:
            authenticator = None
            if tgauthmetadata:
                if not hasattr(tgauthmetadata, "authenticate"):
                    raise TGConfigError("authmetadata in app_cfg missing authenticate.")

                if tgauthmetadata.authenticate is not None:
                    from tg.configuration.auth import create_default_authenticator

                    auth_args, tgauth = create_default_authenticator(
                        tgauthmetadata, **auth_args
                    )
                    authenticator = ("tgappauth", tgauth)

                    if pos is None:
                        auth_args["authenticators"] = [authenticator]
                    else:
                        # We make a copy so that we don't modify the original one.
                        auth_args["authenticators"] = auth_args["authenticators"]
                        auth_args["authenticators"][pos] = authenticator

        from tg.configuration.auth import setup_auth

        app = setup_auth(
            app, skip_authentication=conf["skip_authentication"], **auth_args
        )
        return app
