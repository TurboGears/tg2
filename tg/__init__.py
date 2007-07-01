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
    Give defaults while you give choices
    Give choices while the one obvious way depends

TurboGears 2 as like Ubuntu Linux and Pylons as Debian.
We're focused on user experience, and creating a novice friendly environment.
Pylons provide the power and flexibilty of the underlying core. 
And we don't intend to hide that power and flexibility from advanced users. 

Sensible defaults will be provided but that more powerful mechanisms will be 
available to those projects who need them.


"""
from controllers import TurboGearsController
from decorators import expose, validate
