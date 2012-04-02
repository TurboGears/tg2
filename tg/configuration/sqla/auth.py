# -*- coding: utf-8 -*-
"""
Sample plugins and middleware configuration for :mod:`repoze.who` and
:mod:`repoze.what`.
Mostly took from repoze.what-quickstart.
"""

import sys, logging, copy

from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.who.plugins.sa import SQLAlchemyAuthenticatorPlugin,SQLAlchemyUserMDPlugin
from repoze.who.plugins.friendlyform import FriendlyFormPlugin
from repoze.who.config import _LEVELS

from repoze.what.middleware import setup_auth
from repoze.what.plugins.sql import configure_sql_adapters

__all__ = ("setup_sql_auth")

def copy_dict_keys(d, keys, replacements):
    new_dict = {}
    for index, key in enumerate(replacements):
        old_key = keys[index]
        if old_key in d:
            new_dict[key] = d[old_key]
    return new_dict

def setup_sql_auth(app, user_class, group_class, permission_class,
                   dbsession, form_plugin=None, form_identifies=True,
                   cookie_secret='secret', cookie_name='authtkt',
                   login_url='/login', login_handler='/login_handler',
                   post_login_url=None, logout_handler='/logout_handler',
                   post_logout_url=None, login_counter_name=None,
                   translations={}, cookie_timeout=None,
                   cookie_reissue_time=None, charset="iso-8859-1",
                   use_default_authenticator=True,
                   **who_args):
    """
    Configure :mod:`repoze.who` and :mod:`repoze.what` with SQL-only
    authentication and authorization, respectively.

    :param app: Your WSGI application.
    :param user_class: The SQLAlchemy/Elixir class for the users.
    :param group_class: The SQLAlchemy/Elixir class for the groups.
    :param permission_class: The SQLAlchemy/Elixir class for the permissions.
    :param dbsession: The SQLAlchemy/Elixir session.
    :param form_plugin: The main :mod:`repoze.who` challenger plugin; this is
        usually a login form.
    :param form_identifies: Whether the ``form_plugin`` may and should act as
        an :mod:`repoze.who` identifier.
    :type form_identifies: bool
    :param cookie_secret: The "secret" for the AuthTktCookiePlugin (**set a
        custom one!**).
    :type cookie_secret: str
    :param cookie_name: The name for the AuthTktCookiePlugin.
    :type cookie_name: str
    :param login_url: The URL where the login form is displayed.
    :type login_url: str
    :param login_handler: The URL where the login form is submitted.
    :type login_handler: str
    :param post_login_url: The URL/path where users should be redirected to
        after login.
    :type post_login_url: str
    :param logout_handler: The URL where the logout is handled.
    :type login_handler: str
    :param post_logout_url: The URL/path where users should be redirected to
        after logout.
    :type post_logout_url: str
    :param login_counter_name: The name of the variable in the query string
        that represents the login counter; defaults to ``__logins``.
    :type login_counter_name: str
    :param translations: The model translations.
    :type translations: dict
    :param cookie_timeout: The time (in seconds) during which the session cookie
        would be valid.
    :type cookie_timeout: :class:`int`
    :param cookie_reissue_time: How often should the session cookie be reissued
        (in seconds); must be less than ``timeout``.
    :type cookie_reissue_time: :class:`int`
    :param use_default_authenticator: Whether the default SQL authenticator
        should be used.
    :type use_default_authenticator: :class:`bool`
    :return: The WSGI application with authentication and authorization
        middleware.

    It configures :mod:`repoze.who` with the following plugins:

    * Identifiers:

      * :class:`repoze.who.plugins.friendlyform.FriendlyFormPlugin` as the
        first identifier and challenger -- using ``login`` as the URL/path
        where the login form will be displayed, ``login_handler`` as the
        URL/path where the form will be sent and ``logout_handler`` as the
        URL/path where the user will be logged out. The so-called *rememberer*
        of such an identifier will be the identifier below.

        If ``post_login_url`` is defined, the user will be redirected to that
        page after login. Likewise, if ``post_logout_url`` is defined, the
        user will be redirected to that page after logout.

        You can override the
        :class:`repoze.who.plugins.friendlyform.FriendlyFormPlugin`'s login
        counter variable name (which defaults to ``__logins``) by defining
        ``login_counter_name``.

        .. tip::

            This plugin may be overridden with the ``form_plugin`` argument.
            See also the ``form_identifies`` argument.
      * :class:`repoze.who.plugins.auth_tkt.AuthTktCookiePlugin`. You can
        customize the cookie name and secret using the ``cookie_name`` and
        ``cookie_secret`` arguments, respectively.

      Then it will append the identifiers you pass through the ``identifiers``
      keyword argument, if any.

    * Authenticators:

      * :class:`repoze.who.plugins.sa.SQLAlchemyAuthenticatorPlugin` (unless
        ``use_default_authenticator`` is ``False``), using the ``user_class``
        and ``dbsession`` arguments as its user class and DB session,
        respectively.

      Then it will be appended to the authenticators you pass through the
      ``authenticators`` keyword argument, if any. The default authenticator
      would have the lowest precedence.

    * Challengers:

      * The same Form-based plugin used in the identifiers.

      Then it will append the challengers you pass through the
      ``challengers`` keyword argument, if any.

    * Metadata providers:

      * :class:`repoze.who.plugins.sa.SQLAlchemyUserMDPlugin`, using
        the ``user_class`` and ``dbsession`` arguments as its user class and
        DB session, respectively.

      Then it will append the metadata providers you pass through the
      ``mdproviders`` keyword argument, if any.

    The ``charset`` is passed to any component which needs to decode/encode
    data to/from the user. At present, only
    :class:`~repoze.who.plugins.friendlyform.FriendlyFormPlugin` does.

    Additional keyword arguments will be passed to
    :class:`repoze.who.middleware.PluggableAuthenticationMiddleware`.

    .. warning::

        It's very important to set a custom ``cookie_secret``! It's the key to
        encrypt *and* decrypt the cookies, so you shouldn't leave the default
        one.

    .. note::

        If you don't want to use the groups/permissions-based authorization
        pattern, then set ``group_class`` and ``permission_class`` to ``None``.

    .. versionchanged:: 1.0.5
        Introduced the ``cookie_timeout`` and ``cookie_reissue_time`` arguments.

    .. versionchanged:: 1.0.6
        Introduced the ``charset`` argument.

    .. versionchanged:: 1.0.8
        Introduced the ``use_default_authenticator`` argument.

    """
    plugin_translations = {'group_adapter':copy_dict_keys(translations,
                                                   ['user_name', 'users', 'group_name', 'groups'],
                                                   ['item_name', 'items', 'section_name', 'sections']),
                           'permission_adapter':copy_dict_keys(translations,
                                                        ['group_name', 'groups', 'permission_name', 'permissions'],
                                                        ['item_name', 'items', 'section_name', 'sections']),
                           'authenticator':copy_dict_keys(translations,
                                                   ['validate_password', 'user_name'],
                                                   ['validate_password', 'user_name']),
                           'mdprovider':copy_dict_keys(translations, ['user_name'], ['user_name'])}

    source_adapters = configure_sql_adapters(
        user_class,
        group_class,
        permission_class,
        dbsession,
        plugin_translations['group_adapter'],
        plugin_translations['permission_adapter'])

    group_adapters= {}
    group_adapter = source_adapters.get('group')
    if group_adapter:
        group_adapters = {'sql_auth': group_adapter}

    permission_adapters = {}
    permission_adapter = source_adapters.get('permission')
    if permission_adapter:
        permission_adapters = {'sql_auth': permission_adapter}

    # Setting the repoze.who authenticators:
    if 'authenticators' not in who_args:
        who_args['authenticators'] = []

    if use_default_authenticator:
        sqlauth = SQLAlchemyAuthenticatorPlugin(user_class, dbsession)
        sqlauth.translations.update(plugin_translations['authenticator'])
        who_args['authenticators'].append(('sqlauth', sqlauth))

    cookie = AuthTktCookiePlugin(cookie_secret, cookie_name,
                                 timeout=cookie_timeout,
                                 reissue_time=cookie_reissue_time)

    # Setting the repoze.who identifiers
    if 'identifiers' not in who_args:
        who_args['identifiers'] = []
    who_args['identifiers'].append(('cookie', cookie))

    if form_plugin is None:
        form = FriendlyFormPlugin(
            login_url,
            login_handler,
            post_login_url,
            logout_handler,
            post_logout_url,
            login_counter_name=login_counter_name,
            rememberer_name='cookie',
            charset=charset,
            )
    else:
        form = form_plugin

    if form_identifies:
        who_args['identifiers'].insert(0, ('main_identifier', form))

    # Setting the repoze.who challengers:
    if 'challengers' not in who_args:
        who_args['challengers'] = []
    who_args['challengers'].append(('form', form))

    # Setting up the repoze.who mdproviders:
    sql_user_md = SQLAlchemyUserMDPlugin(user_class, dbsession)
    sql_user_md.translations.update(plugin_translations['mdprovider'])
    if 'mdproviders' not in who_args:
        who_args['mdproviders'] = []
    who_args['mdproviders'].append(('sql_user_md', sql_user_md))

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

    middleware = setup_auth(app, group_adapters, permission_adapters,
                            **who_args)
    return middleware
