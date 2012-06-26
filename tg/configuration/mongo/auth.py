# -*- coding: utf-8 -*-
from tgming.auth import MingAuthenticatorPlugin

def create_default_authenticator(user_class, translations=None, **unused):
    mingauth = MingAuthenticatorPlugin(user_class)
    return unused, mingauth
