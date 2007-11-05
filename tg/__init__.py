"""
TurboGears 2 is a reinvention of TurboGears and a return to TurboGears' roots.

TurboGears is a project that is built upon a foundation of reuse and building up. 
In retrospect, much of the code that was home grown in the TurboGears project 
should have been released as independent projects that integrate with TurboGears. 
This would have allowed better growth of those pieces.

TurboGears 0.5 release was just a few hundred lines of Python code that 
built upon thousands of lines of other libraries.

Now TurboGears2 is built on Pylons and allows you to use 
your favorite Python components and libraries::

    * Models: SQLAlchemy, SQLObject, plain old DB-API
    * Template engines: Genshi, Kid, Myghty, Mako, Cheetah, or whatever you like - using Buffet
    * URL Dispatching: Object dispatch, Routes, or plug in your favorite
    * AJAX: ToscaWidgets, WebHelpers based on Prototype or Mochikit, Dojo, JQuery, Ext & more

The zen of TurboGears is::

    Keep simple things simple and complex things possible
    Give god defaults everywhere and allow choices where they matter
    Don't pretend that there's one obvious way, when there isn't

TurboGears 2 is to Pylons as Ubuntu is to Debian Debian.

We're focused on user experience, and creating a user friendly environment.
We make choices, setup sane defaults, and build on top of a powerfull, flexible core. 
Pylons provide that core, and focuses on maximizing flexibility, stability. 

we don't intend to hide that power and flexibility from advanced users, we just want
them to be able to get up and running quickly, and have a well lit development path
to walk. 


"""
from controllers import TurboGearsController

from pylons.decorators import expose, new_validate as validate
from pylons.wsgiapp import PylonsApp
from pylons import c as context
from pylons import g as app_globals
from pylons import request
from pylons import session


class TurboGearsApplication(PylonsApp):
    def __init__(self, root, **kwargs):
        PylonsApp.__init__(self, **kwargs)
        self.root = root

    def resolve(self, environ, start_response):
        return self.root

    def __call__(self, environ, start_response):
        environ['pylons.routes_dict'] = {}
        self.setup_app_env(environ, start_response)
        return self.root(environ, start_response)


__all__ = [
    'expose', 'validate', 'TurboGearsController', 'context', 'app_globals', 
    'request', 'TurboGearsApplication', 'session'
]