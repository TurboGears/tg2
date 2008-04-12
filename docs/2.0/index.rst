

:Status: Official

TurboGears 2 is a reinvention of the TurboGears project to take advantage of new components, and to provide a fully custmizable WSGI enabled stack.  

At the moment TurboGears 2 is still in rapid development, and should only be used by those who are willing to put up with a little bit of API instability.  If you want to use TG2 at the moment, you will have to download SVN and Mercurial, and check both TG2 and Pylons out from their respective version control system:

* `Installation Instructions <DownloadInstall>`_

The documentation for TurboGears 2 is evolving rapidly, and there are a number of as yet unofficial docs located here:
 
* `2.0/RoughDocs`_


Installation and deployment guides
-----------------------------------


* `How to install TurboGears 2 <DownloadInstall>`_
* `Offline installation Guide <OfflineInstall>`_
* `Deployment <Deployment>`_


Architecture and Organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- `The Big Picture <GettingStarted/BigPicture>`_


Screencasts
~~~~~~~~~~~

No 2.0 screencasts yet... 

TG2 Related Tutorials 
~~~~~~~~~~~~~~~~~~~~~~~

* `Quickstart <Quickstart>`_ -- How to start a TurboGears project.

* `TurboGears 2 at a glance <BasicMoves>`_  -- How the simplest possible TG2 application works, with some information on what the Model View Controller pattern looks like in web development, and how  the TG2 application structure works. 

* `20 Minute Wiki <Wiki20/All>`_  -- Learn to build a simple Wiki in TurboGears 2.  This tutorial provides a quick introduction to the basic components of TurboGears2 and leads you quickly through the creation of a very simple application.  If you're getting started with TurboGears 2, without experience in TG1, the Wiki tutorial is a great place to get started.  It walks you through creating a simple Wiki application in TurboGears 2, explaining the various parts of TG2 as you go. 



Writing Controller code:
~~~~~~~~~~~~~~~~~~~~~~~~~~




Writing View and Template code:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~




Writing SQLAlchemy Model code: 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~





Handing Forms and Validation:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Creating Reusable Widgets:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



Documentation by Component
--------------------------

TG2 is built from many existing components, many of which are independently useful, and many of which are documented throughly elsewhere on the web. 

* Babel (localization and internationalization)

* Beaker (Caching and sessions) 

* DBSprockets (Automatic form generation) 

* FormEncode (Validator creation) 

* Genshi (Templating)

* Routes (Provides an alternative to Object Dispatch)

* `ToscaWidgets <ToscaWidgets>`_

* SQLAlchemy (SQL tools and Object Relational Mapper) 
  
  * ORM Tutorial  
  
  * SQLExpressoin Tutorial
  
* WebOb (request and response objects)


Authority
~~~~~~~~~~

* `Authority Overview <Authority>`_


Controller Decorators
~~~~~~~~~~~~~~~~~~~~~

* `@expose <ExposeDecorator>`_

* `@validate <ValidateDecorator>`_

* `@authority.require <IdentityDecorator>`_

* `@paginate <PaginateDecorator>`_

* `@etag and @cache <caching>`_


Tests and Logging
~~~~~~~~~~~~~~~~~~

* `Agile Testing: testutil and nosetests <Testing>`_

* `Error Logging: The TurboGears Logging System <Logging>`_


Other Topics
~~~~~~~~~~~~

* `Internationalization <Internationalization>`_

* `Using Your Model Outside of TurboGears applications <ModelOutsideTG>`_

* `Automatic JSON Serialization: json.py and the @jsonify.when Decorator <JsonifyDecorator>`_


Community
---------

* Discuss in `Mailing Lists <1.0/GettingHelp>`_ (users, developers, and non-
  english groups)

* Chat in the `IRC channel <irc://irc.freenode.net/turbogears>`_ 

* Watch `Sites Using TurboGears <SitesUsingTurboGears>`_

* Download `TurboGears Applications <TurboGearsApplications>`_

* Find TurboGears Extensions and Plugins in the 
  `CogBin <http://www.turbogears.org/cogbin/>`_

* Follow Latest Activity on `Planet TurboGears <http://planet.turbogears.org/>`_

* Find Professional `TurboGears Developers or Trainers <TurboGearsConsultants>`_


Contributing to TurboGears
~~~~~~~~~~~~~~~~~~~~~~~~~~

* `TurboGears Philosophy <TG2Philosophy>`_

* `License <License>`_

* `Development Status <DevStatus>`_

* `Who is Who: the TurboGears Development Team <TurboGearsTeam>`_

* `Reporting Bugs and Feature Requests with Trac <http://trac.turbogears.org/>`_

* `Contributing Code <Contributing>`_

* `Writing Documentation <DocHelp>`_


Reference
---------

* Reference Docs need to be generated/written


Resources
---------

* `Link List <TurboGearsBookMarks>`_ with TurboGears-related Resources


----

Adding Documentation
--------------------

You can add your feedback to any document by adding a comment, or you can 
contribute an article in RoughDocs_. See also `Writing Documentation <DocHelp>`_


----

 | `Home <http://www.turbogears.org>`_ · FrontPage_ · `CogBin <http://www.turbogears.org/cogbin/>`_ · `News <News>`_ · `Links <TurboGearsBookMarks>`_
