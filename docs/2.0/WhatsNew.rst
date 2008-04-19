The most significant change in TurboGears 2 is the decision to work very, very closely with Pylons.   We've basically built a copy of the TG 1.x API on top of pylons/paste which allows our two communities to work together on everything from internationalization to database connection pooling.     

Another significant change is that we've removed the tg-admin wrapper and started explicitly using paster for administrative commands to match what Pylons was doing.   We've re-implemented the old tg-admin commands as  paster commands; for example, "tg-admin quickstart" is replaced by "paster quickstart". 

The "why" of TurboGears 2
------------------------------

Lots of questions have been asked about why we've decided to create TurboGears 2 the way we did,  so let's try to answer them as best we can.   

Why so many changes?
~~~~~~~~~~~~~~~~~~~~~~

Well, there are a lot of changes, but perhaps not as many as it looks like from the description.  We were able to keep the controller API very similar to TG1, and Genshi copied the Kid API, so while we chose new components, we didn't really change the way Controllers and Templates look very much at all.  Sure, there are some minor changes here and there, but one member of the TG2 training class at PyCon said "I didn't notice a lot that was new in terms of how you put a TurboGears application together." 

Why not just merge with Pylons?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Well, pylons is committed to being officially template engine agnostic, ORM agnostic, etc.  On the other hand TurboGears is committed to providing a "Full-Stack" for web development.  So, the two communities have different, but compatible priorities.  If you think about it Pylons provides a great set of tools for building a full stack framework, and people had been asking for a full-stack pylons implementation for a long time.   And TurboGears 2 will provide that. 

There are a lot of benifits to having a full-stack.  You can build form helpers which do all sorts of interesting things (introspect model objects to make web-based forms, automatically display form errors, etc) because you can make some assumptions about what tools will be available and what will be used.    In particular, you can start building plugable website components much more easily, because you are building on a known set of tools. 

Why not use CherryPy 3?
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is something we really struggled with.  CherryPy 3 is a huge improvement over CherryPy 2, providing a much richer programming experience, and huge performance gains.  But TurboGears 1 was very tightly coupled to the config system of CherryPy 2, which was entirely rewritten in CherrPy 3.   We tried to make a backwards compatible TG based on CherryPy 3, but discovered that it was significantly more difficult than we had expected.   

At the same time there was a push to make TurboGears 2 more WSGI based, and to take adval

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
   


