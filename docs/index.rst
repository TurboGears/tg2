TurboGears Documentation:
=============================

TurboGears 2 is a reinvention of the TurboGears project to take advantage of 
new components, and to provide a fully customizable WSGI (Web Server Gateway 
Interface) stack.  From the beginning TurboGears was designed to be a Full 
Stack framework built from best-of-breed components. New components have been 
released which improved on the ones in the original TGstack, and the Python 
web world has been increasingly designed around WSGI.  

This has enabled a whole new world of component reuse, and TG2 is designed to 
take advantage of this fact in order to make a framework which is both 
flexible, and productive.  TG2 represents a change from TurboGears 1, but it 
also represents a set of components that we think will continue to be at 
the center of python web development for years to come. 

TurboGears 2 is in rapid development, and those who jump onboard now may 
experience a bit of API instability that comes from all that development 
energy, but because it is well tested, and based on well tested, and known 
stable components it is already being used by some people in production 
environments.

Getting Started with TurboGears
==================================

Get TurboGears 2 installed, learn how to create a new TurboGears project in a 
single command, and of course explore the obligatory "Hello World" example, 
with a few fun treats thrown in.

.. toctree::
   :maxdepth: 2

   main/DownloadInstall
   main/QuickStart
   main/BasicMoves

Tutorials
===========

Are you the type who learns by doing?   If so this section is for you.  Our 
ultimate goal is to provide several tutorials on TG2 including everything 
from the basics, to advanced topics.

.. toctree::
   :maxdepth: 2
   
   main/Wiki20/wiki20
   main/ToscaWidgets/forms

What's new
===============

.. toctree::
   :maxdepth: 2

   main/WhatsNew

General Reference for MVC Components
======================================

.. toctree::
   :maxdepth: 2

   main/Controllers
   main/Genshi
   main/SQLAlchemy

Validation, Form handling and form widgets
===========================================

.. toctree::
   :maxdepth: 2

   main/FormBasics
   main/Validation
   main/ToscaWidgets/forms
   main/ToscaWidgets/ToscaWidgets


Recipes for Installation and Deployment
========================================

.. toctree::
   :maxdepth: 2

   main/OfflineInstall
   main/Deployment
   main/Deployment/ModProxy
   main/Deployment/modwsgi+virtualenv


Development Tools
======================

.. toctree::
   :maxdepth: 2

   main/ToolBox
   main/CommandLine
   main/Profile

   main/RoughDocs/CreateDatabase
   main/RoughDocs/BootStrap
   main/ToscaWidgets/Using
   main/SimpleWidgetForm


Other TG Tools
=====================

.. toctree::
   :maxdepth: 2
   
   main/Config
   main/Caching
   main/Auth
   main/LogSetup
   main/Internationalization



Recipes
======================

.. toctree::
   :maxdepth: 2

   main/TGandPyAMF
   main/RoutesIntegration
   main/StaticFile
   main/Mako
   main/Jinja

Performance and optimization:
===============================

Not all sites are going to be performance constrained, and not all performance
constraints are created equal.   Premature optimization can get you into a lot 
of trouble if you're not careful, but at the same time knowing and doing a 
few simple things up front can help you to handle huge traffic loads when they
come.   

These guides are not intended to be exhaustive descriptions of web-application
performance and scalability issues, but rather to provide some simple advice
for those who are expecting large traffic loads. 

.. toctree::
   :maxdepth: 2
   
   main/GeneralPerformance
   main/TemplatePerformance
   main/DatabasePerformance



General Project Information
=======================================

.. toctree::
   :maxdepth: 2

   main/TG2Philosophy
   main/DevStatus
   main/Contributing
   main/License
   main/TGandPylons

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

