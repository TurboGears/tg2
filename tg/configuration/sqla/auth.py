# -*- coding: utf-8 -*-
from repoze.who.plugins.sa import SQLAlchemyAuthenticatorPlugin

def create_default_authenticator(user_class, dbsession, translations=None, **unused):
    sqlauth = SQLAlchemyAuthenticatorPlugin(user_class, dbsession)
    if translations is not None:
        sqlauth.translations.update(translations)
    return unused, sqlauth
