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

TurboGears 2 is committed to the following Python components and libraries,
which are backwards compatible with TurboGears 1.1:

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

While TurboGears2 is not based on Pylons anymore it's still focused on user experience,
and creating a novice-friendly environment.
We ship a smaller subset of components, and thus are better able
to focus, test, and document things so that new users have the best possible
experience.

Sensible defaults encourage code re-use within TurboGears because
they make it possible for a group of TurboGears components to share
assumptions about how things will work.

"""

from . import i18n
from .configuration import config, milestones
from .configuration.app_config import AppConfig
from .configurator import (
    ApplicationConfigurator,
    Configurator,
    FullStackApplicationConfigurator,
    MinimalApplicationConfigurator,
)
from .controllers import RestController, TGController
from .controllers.dispatcher import dispatched_controller
from .controllers.util import (
    abort,
    auth_force_login,
    auth_force_logout,
    etag_cache,
    redirect,
    use_wsgi_app,
    validation_errors_response,
)
from .decorators import (
    cached,
    decode_params,
    expose,
    override_template,
    require,
    use_custom_format,
    validate,
    with_engine,
)
from .flash import flash
from .jsonify import encode as json_encode
from .render import render as render_template
from .request_local import (
    Request,
    Response,
    app_globals,
    cache,
    request,
    response,
    session,
    tmpl_context,
    translator,
)
from .support.hooks import hooks
from .support.url import lurl, url
from .wsgiapp import TGApp

__all__ = (
    "app_globals",
    "expose",
    "override_template",
    "request",
    "hooks",
    "config",
    "AppConfig",
    "ApplicationConfigurator",
    "Configurator",
    "RestController",
    "abort",
    "flash",
    "redirect",
    "translator",
    "validation_errors_response",
    "auth_force_login",
    "auth_force_logout",
    "etag_cache",
    "use_wsgi_app",
    "require",
    "response",
    "session",
    "TGApp",
    "TGController",
    "tmpl_context",
    "use_wsgi_app",
    "validate",
    "i18n",
    "json_encode",
    "cache",
    "url",
    "lurl",
    "dispatched_controller",
    "use_custom_format",
    "with_engine",
    "render_template",
    "Request",
    "Response",
    "cached",
    "decode_params",
    "milestones",
    "MinimalApplicationConfigurator",
    "FullStackApplicationConfigurator",
)
