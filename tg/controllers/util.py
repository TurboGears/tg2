# -*- coding: utf-8 -*-
"""Helper functions for controller operation.

URL definition and browser redirection are defined here.

"""

from ..configuration.utils import TGConfigError
from ..request_local import request as tg_request
from ..request_local import response as tg_response
from ..support.responses import abort, etag_cache, redirect, validation_errors_response
from ..support.url import lurl, url


def use_wsgi_app(wsgi_app):
    return tg_request.get_response(wsgi_app)


def auth_force_login(user_name):
    """Forces user login if authentication is enabled.

    As TurboGears identifies users by ``user_name`` the passed parameter should
    be anything your application declares being the ``user_name`` field in models.

    """
    req = tg_request._current_obj()
    resp = tg_response._current_obj()

    api = req.environ.get("repoze.who.api")
    if api:
        authentication_plugins = req.environ["repoze.who.plugins"]
        try:
            identifier = authentication_plugins["main_identifier"]
        except KeyError:
            raise TGConfigError('No repoze.who plugin registered as "main_identifier"')

        resp.headers.extend(
            api.remember({"repoze.who.userid": user_name, "identifier": identifier})
        )


def auth_force_logout():
    """Forces user logout if authentication is enabled."""
    req = tg_request._current_obj()
    resp = tg_response._current_obj()

    api = req.environ.get("repoze.who.api")
    if api:
        resp.headers.extend(api.forget())


__all__ = (
    "url",
    "lurl",
    "redirect",
    "etag_cache",
    "abort",
    "auth_force_logout",
    "auth_force_login",
    "validation_errors_response",
    "use_wsgi_app",
)
