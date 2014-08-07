"""TurboGears 2 is a reinvention of TurboGears and a return to TurboGears' roots.

TurboGears is a project that is built upon a foundation of library development
best-of-breed component selection, and the re-use of already existing code.
And it was always intended to be a small collection of tools, docs, and helpers
that made developing with that best-of-breed stack easy.

In retrospect, some of the code that was added to the main TurboGears project
should have been released as independent projects that integrate with
TurboGears. This would have allowed those pieces to grow independently of
TurboGears, and would have allowed TurboGears to remain smaller and easier
to develop and debug.

TurboGears 0.5 release was just a few hundred lines of Python code, but it
built on thousands of lines of code in other libraries. Those libraries had
already been deployed, used, and tested, and were known to be
"production ready."

TurboGears2 returns to that philosophy. It is built on Pylons, but it brings
a best-of-breed approach to Pylons. TurboGears 2 is commited to the following
Python components and libraries, which are backwards compatable with
TurboGears 1.1:

    * Models: SQLAlchemy
    * Template engines: Genshi
    * URL Dispatching: Object dispatch
    * Form Handling: ToscaWidgets

The zen of TurboGears is::

    Keep simple things simple and complex things possible
    Give good defaults everywhere and allow choices where they matter
    Do your best to do things the right way,
    But when there's no "one right way," don't pretend there is.

Mark Ramm described the relationship between TurboGears and Pylons this way
"TurboGears 2 is to Pylons as Ubuntu is to Debian."

In other words we're focused on user experience, and creating a novice-friendly
environment. We ship a smaller subset of components, and thus are better able
to focus, test, and document things so that new users have the best possible
experience.

Meanwhile Pylons provides the power and flexibility of the underlying core.

And like Ubuntu, we don't intend to hide that power and flexibility from
advanced users, but we know that they want things set up to just work too.

Sensible defaults encourage code re-use within TurboGears because
they make it possible for a group of TurboGears components to share
assumptions about how things will work.

"""

from tg.request_local import app_globals, request, response, tmpl_context, session, cache, translator
from tg.configuration import config, AppConfig
from tg.wsgiapp import TGApp
from tg.controllers import TGController, RestController, redirect, url, lurl, abort
from tg.release import version
from tg.decorators import (validate, expose, override_template, use_custom_format,
                           require, with_engine, cached, decode_params)

from tg.flash import flash, get_flash, get_status
from tg.jsonify import encode as json_encode
from tg.controllers.util import *
from tg.controllers.dispatcher import dispatched_controller
from tg.render import render as render_template
from tg.configuration.hooks import hooks

from tg.request_local import Request, Response

__version__ = version

__all__ = ['__version__',
    'app_globals', 'expose', 'override_template', 'request',
    'require', 'response', 'session', 'TGApp', 'TGController', 'tmpl_context',
    'use_wsgi_app', 'validate', 'i18n','json_encode', 'cache', 'url', 'lurl',
    'dispatched_controller', 'use_custom_format', 'with_engine', 'render_template',
    'Request', 'Response', 'cached', 'decode_params']
