


:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2


What's new in TurboGears 2:
===============================

The most significant change in TurboGears 2 is the decision to work very, very closely with Pylons.   We've basically built a copy of the TG 1.x API on top of pylons/paste  which allows our two communities to work together on everything from internationalization to database connection pooling and threading strategies.     

Another significant change is that we've removed the tg-admin wrapper and started explicitly using paster for administrative commands to match what Pylons was doing.   We've reimplemented the old tg-admin commands as  paster commands; for example, "tg-admin quickstart" is replaced by "paster quickstart". 

Main decisions
---------------

  * Based on Pylons instead of based on CherryPy
  * Use SQLAlchemy as default ORM, but provide for SQLObject
  * Use genshi as the default template engine, but provide support for Kid, Mako and others

NOTE: SQLObject support is not yet completed. 

New Features to TurboGears 2:
------------------------------

  * Cache system
  * Error report: interactive tracebacks through the web, custom error pages, and email alerts
  * API Document generator through epydoc
  * could pass status code to flash message
  * support crud interface generator

Compatibility
---------------

  * Possibly deprecate the python 2.3 support?
  * TurboGears 1.x and TurboGears 2.x could be installed in the same machine. They are different packages with different namespaces.
  * Object dispatch is implemented in TurboGears 2.x, so you can use arguments and keywords in function as in TurboGears 1.x.
  * Expose and error handling decorators are implemented in TurboGears 2.x, you can use decorators just like TurboGears 1.x.
  * CherryPy filters will not work in TurboGears 2.x.  You can easily write middleware to do what filters did in CherryPy2
  * The @expose decorator has a slightly updated syntax for content type declaration 
  * All template engines now have search paths to find the templates.  The default template directory is on the search path so using dotted notation in @expose decorators has been deprecated.
  * Rather than raise a redirect error, you now call the redirect_to()  function

Command changes
----------------

Use paster command instead of tg-admin command.

  * tg-admin quickstart -> paster quickstart
  * tg-admin info -> paster tginfo
  * tg-admin toolbox -> paster toolbox

Project layout changes 
------------------------

Both controllers.py and model.py are now folders, as they have been changed to be Python packages.

  * controllers.py -> move to controllers/root.py
  * model.py -> model/model.py
    * SQLObject -> Elixir over SQLAlchemy, check for 1.0->1.1 guide
  * templates/ -> templates/
    * kid -> genshi, check for 1.0->1.1 guide
  * dev.ini -> development.ini
    config/config.ini -> config/environments.py and middleware.py


Function changes 
--------------------

  * different name space: import turbogears -> import tg
  * turbogears.config.get('sqlalchemy.dburi') -> pylons.config['sqlalchemy.default.dburi']

In progress
-------------

  * static -> public
        static file urls: /static -> /
  * tg-admin sql create -> paster setup.py make-app development.ini
  * model transcations
  * toscawidget integration
   


