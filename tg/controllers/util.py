# -*- coding: utf-8 -*-
"""
Helper functions for controller operation.

Url definition and browser redirection are defined here.
"""

import pylons
from pylons import url as pylons_url
from tg.decorators import expose

from tg.exceptions import HTTPFound


def url(*args, **kwargs):
    """Generate an absolute URL that's specific to this application.

    The URL function takes a string, appends the SCRIPT_NAME and adds url
    parameters for all of the other keyword arguments passed in.

    For backwards compatibility you can also pass in a params dictionary
    which is turned into url params, or you can send in a a list of
    strings as the first argument, which will be joined with /'s to
    make a url string.

    In general tg.url is just a proxy for pylons.url which is in turn
    a proxy for routes url_for function.  This means that if the first
    argument is not a basestring but a method that has been routed to,
    the standard routes url_for reverse lookup system will be used.
    """
    args = list(args)
    if isinstance(args[0], list):
        args[0] = u'/'.join(args[0])
    if args and isinstance(args[0], basestring):
        #First we handle the possibility that the user passed in params
        if isinstance(kwargs.get('params'), dict):
            params = kwargs['params'].copy()
            del kwargs['params']
            params.update(kwargs)
            kwargs = params

        if len(args) >= 2 and isinstance(args[1], dict):
            params = args[1].copy()
            if kwargs:
                params.update(kwargs)
            kwargs = params
            args.pop(1)

        if isinstance(args[0], unicode):
            args[0] = args[0].encode('utf8')
    return pylons_url(*args, **kwargs)

def redirect(*args, **kwargs):
    """Generate an HTTP redirect.

    The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the
    second request.
    """

    url(*args, **kwargs)
    found = HTTPFound(location=url(*args, **kwargs)).exception

    raise found

def use_wsgi_app(wsgi_app):
    return wsgi_app(pylons.request.environ, pylons.request.start_response)


# Idea stolen from Pylons
def pylons_formencode_gettext(value):
    from pylons.i18n import ugettext as pylons_gettext
    from gettext import NullTranslations

    trans = pylons_gettext(value)

    # Translation failed, try formencode
    if trans == value:

        try:
            fetrans = pylons.c.formencode_translation
        except AttributeError, attrerror:
            # the translator was not set in the Pylons context
            # we are certainly in the test framework
            # let's make sure won't return something that is ok with the caller
            fetrans = NullTranslations()

        if not fetrans:
            fetrans = NullTranslations()

        trans = fetrans.ugettext(value)

    return trans

__all__ = [
    "url", "redirect"
    ]
