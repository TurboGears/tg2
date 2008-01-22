"""
TurboGears 2 is a reinvention of TurboGears and a return to TurboGears' roots.

TurboGears is a project that is built upon a foundation of library development best-of-breed component selection, and the re-use of already existing code. And it was always intended to be a small collection of tools, docs, and helpers that made developing with that best-of-breed stack easy.

In retrospect, some of the code that was added to the main TurboGears project should have been released as independent projects that integrate with TurboGears. This would have allowed those pieces to grow independently of TurboGears, and would have allowed TurboGears to remain smaller and easier to develop and debug.

TurboGears 0.5 release was just a few hundred lines of Python code, but it built on thousands of lines of code in other libraries. Those libraries had alreay been deployed, used, and tested, and were known to be "production ready."

TurboGears2 returns to that philosophy. It is built on Pylons, but it brings a best-of-breed approach to Pylons. TurboGears 2 is commited to the following Python components and libraries, which are backwards compatable with TurboGears 1.1:

    * Models: SQLAlchemy
    * Template engines: Genshi
    * URL Dispatching: Object dispatch
    * Form Handling: ToscaWidgets
    
The zen of TurboGears is::

    Keep simple things simple and complex things possible
    Give good defaults everywhere and allow choices where they matter
    Do your best to do things the right way,
    But when there's no "one right way," don't pretend there is.

Mark Ramm described the relationship between TurboGears and Pylons this way "TurboGears 2 is to Pylons as Ubuntu is to Debian."

In other words we're focused on user experience, and creating a novice-friendly environment. We ship a smaller subset of components, and thus are better able to focus, test, and document things so that new users have the best possible experience.

Meanwhile Pylons provides the power and flexibility of the underlying core.

And like Ubuntu, we don't intend to hide that power and flexibility from advanced users, but we know that they want things set up to just work too.

Sensible defaults actually encourage code re-use within TurboGears because they make it possible for a group of TurboGears components to share assumptions about how things will work.
"""
from tg.controllers import TurboGearsController, redirect, url
from tg.flash import flash, get_flash, get_status

import paste
from pylons.decorators import expose, new_validate as validate
from pylons.wsgiapp import PylonsApp
from pylons import c as context
from pylons import g as app_globals
from pylons import request
from pylons import session


class TurboGearsApplication(PylonsApp):
    """basis TurboGears application class which is derived from PylonsApp"""
    def __init__(self, root, **kwargs):
        # see ticket #1687
        kwargs['use_webob'] = False
        PylonsApp.__init__(self, **kwargs)
        self.root = root

    def resolve(self, environ, start_response):
        return self.root

    def __call__(self, environ, start_response):

        environ['pylons.routes_dict'] = {}
        self.setup_app_env(environ, start_response)

        # Initialize config if this is called by "paster shell"
        # as indicated by the fact that the shell sets a special
        # PATH_INFO
        if 'paste.testing_variables' in environ:
            self.load_test_env(environ)
            if environ['PATH_INFO'] == '/_test_vars':
                paste.registry.restorer.save_registry_state(environ)
                start_response('200 OK', [('Content-type', 'text/plain')])
                return ['%s' % paste.registry.restorer.get_request_id(environ)]

        return self.root.__class__()(environ, start_response)


__all__ = [
    'expose', 'validate', 'TurboGearsController', 'context', 'app_globals',
    'request', 'TurboGearsApplication', 'session'
]
