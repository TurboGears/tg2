What's new in TurboGears 2
===========================

The most significant change in TurboGears 2 is the decision to work very, very closely with Pylons.   We've basically built a copy of the TurboGears 1.x API on top of pylons/paste which allows our two communities to work together on everything from internationalization to database connection pooling.     

Another significant change is that we've removed the tg-admin wrapper and started explicitly using paster for administrative commands to match what Pylons was doing.   We've re-implemented the old tg-admin commands as  paster commands; for example, "tg-admin quickstart" is replaced by "paster quickstart". 

The "why" of TurboGears 2
------------------------------

Lots of questions have been asked about why we've decided to create TurboGears 2 the way we did,  so let's try to answer them as best we can.   

Why so many changes?
~~~~~~~~~~~~~~~~~~~~~~

Well, there are a lot of changes, but perhaps not as many as it looks like from the description.  We were able to keep the controller API very similar to TurboGears 1, and Genshi copied the Kid API, so while we chose new components, we didn't really change the way Controllers and Templates look very much at all.  Sure, there are some minor changes here and there, but one member of the TurboGears 2 training class at PyCon said "I didn't notice a lot that was new in terms of how you put a TurboGears application together." 

Why not just merge with Pylons?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Well, pylons is committed to being officially template engine agnostic, ORM agnostic, etc.  On the other hand TurboGears is committed to providing a "Full-Stack" for web development.  So, the two communities have different, but compatible priorities.  If you think about it Pylons provides a great set of tools for building a full stack framework, and people had been asking for a full-stack pylons implementation for a long time.   And TurboGears 2 will provide that.

There are a lot of benefits to having a full-stack.  You can build form helpers which do all sorts of interesting things (introspect model objects to make web-based forms, automatically display form errors, etc) because you can make some assumptions about what tools will be available and what will be used.    In particular, you can start building plugable website components much more easily, because you are building on a known set of tools. 

Why not use CherryPy 3?
~~~~~~~~~~~~~~~~~~~~~~~~~~

This is something we really struggled with.  CherryPy 3 is a huge improvement over CherryPy 2, providing a much richer programming experience, and huge performance gains.  But TurboGears 1 was very tightly coupled to the config system of CherryPy 2, which was entirely rewritten in CherrPy 3.   We tried to make a backwards compatible TG based on CherryPy 3, but discovered that it was significantly more difficult than we had expected.   

At the same time there was a push to make TurboGears 2 more WSGI based, and to take advantage of things like Routes middleware, and to generally take advantage of the Pylon WSGI revolution.   We discovered that Pylons had a lot of the same code as TurboGears (both of us had buffet implementations both of us had SQLObject wrappers that did the same thing, etc)

Why Genshi?
~~~~~~~~~~~~~~~~~~~

Well, Genshi is an intentional re-implementation of Kid, with a almost identical API.   But internally it's simpler, faster, and provides better error messages.   The inclusion of a couple of new features -- includes and full x-path support -- also make it significantly more flexible.   

Genshi has also developed a larger, more active community than Kid, and is being used in lots of places outside of TurboGears so, unlike Kid, it's not at all likely to have to be taken over and maintained by the TG core developers. 

Why SQLAlchemy?
~~~~~~~~~~~~~~~~~~~


New Features to TurboGears 2:
------------------------------

  * Cache system
  * Error report: interactive tracebacks through the web, custom error pages, and email alerts
  * API Document generator through epydoc
  * could pass status code to flash message
  * support crud interface generator

Compatibility
---------------

Areas of compatibility:
 
  * Like TurboGears 1.1, TurboGears 2 supports python 2.4 and above.   
  * TurboGears 1.x and TurboGears 2.x can both be installed in the same machine. 
    They are different packages with different namespaces.  Right now there are no dependency conflicts.  But using virtualenv to is highly recommended to eliminate the possibility of future dependency conflicts. 
  * Object dispatch is implemented in TurboGears 2.x, so you can use arguments and keywords in function the same way you did in TurboGears 1.x.
  * Expose and error handling decorators are implemented in TurboGears 2.x, 
    you can use decorators just like TurboGears 1.x.
    

Differences:    
  * CherryPy filters will not work in TurboGears 2.x.  You can write 
    middleware to do what filters did in CherryPy2
  * The @expose decorator has a slightly updated syntax for content type declaration 
  * All template engines now have search paths to find the templates.  
    The default template directory is on the search path so using dotted 
    notation in @expose decorators has been deprecated.
  * Rather than raise a redirect error, you now call the redirect() function.
  * Object dispatch does not support dots in URL's the way TurboGears 1 did. 
  * CherryPy request and response objects replaces with WebOb request and response objects. 
  
Command changes
----------------

Use paster command instead of the old tg-admin command.

For exampel you now type ``paster quickstart`` rather than ``tg-admin quickstart`` to start a project. 

Here's a full list of the old command line tools and their new equivalents

  * ``tg-admin quickstart`` ---> ``paster quickstart``
  * ``tg-admin info`` ---> ``paster tginfo``
  * ``tg-admin toolbox`` --> ``paster toolbox``
  * ``tg-admin shell`` --> ``paster shell``
  * ``tg-admin sql create`` --> ``paster setup-app development.ini``

Project layout changes 
------------------------

Both controllers.py and model.py have been replaced by the controllers and model folders.  In other words there are now Python packages, in just the way they were in TurboGears 1 if you used the '--template tgbig' option with quickstart. 

  * your root controller is not in ``controllers.py`` -> it has moved to ``controllers/root.py``
  * ``model.py`` -> ``model/__init__.py``
  * ``myproject_dev.cfg`` -> ``development.ini`` **With a whole new structure based on paste.deploy**
  * ``app.cfg`` -->  ``config/environment.py`` and to a lesser extent ``config/middleware.py``


New imports 
-------------

  * import turbogears -> import tg
  * turbogears.config.get('sqlalchemy.dburi') -> pylons.config['sqlalchemy.url']
  * pylons.tmpl_context provides a request local place to stick stuff
  * pylons.request  provides the rough equivelent of cherrypy.request
  * pylons.response provides the equivelent of cherrypy.response

