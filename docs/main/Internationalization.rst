

Handling internationalization and localization
===============================================

:Status: Work in progres

.. contents:: Table of Contents
    :depth: 2

Turbogears2 relies on Pylons and Babel for i18n and l18n support. So you want 
to check their respective documentation:

 * Pylons' `Internationalization and Localization`_ doc (which also contains 
   "Using Babel" section)
 * Babel's UserGuide_

A quickstarted project comes fully i18n enabled so you should get started 
quickly.

If you're lucky enough you'll even see "Your application is now running" 
message in your language.  

Language auto-select
--------------------

Turbogears2 contains the logic (hardwired in the TurboGearsController class 
at the moment) to setup request's language based on browser's preferences(*). 

[*] - Every modern browser sends a special header along with every web 
request which tells the server which language it would prefer to see in a 
response. 


An il8n Quick Start
-------------------

After quickstart your project, you could go with the following steps:

1. Create a translation catalog for your language, let's take 'zh_tw' for 
   example::

    python setup.py init_catalog -l zh_tw

2. Edit your language in il8n/[country code]/LC_MESSAGES/[project-name].po  

3. Compile your lang::

    python setup.py compile_catalog  

4. Config development.ini::

    [app:main]
    use = egg: my-project
    full_stack = true
    lang = zh_tw

5. Start server::

    paster serve --reload development.ini

And see the local message show on the screen.


Commands
---------


To fresh start a translation, you could use following command to handle your 
locales:

init_catalog
~~~~~~~~~~~~~

You can extract all messages from the project with the following command::

  python setup.py init_catalog -l [country code]

The country code could be es(Spanish), fr(France), zh_tw(Taiwan), jp(JAPAN), 
ru(Russian), or any other country code.

Compile Catalog
~~~~~~~~~~~~~~~~

You can extract all messages from the project with the following command::

  python setup.py compile_catalog

Update Catalog
~~~~~~~~~~~~~~~

You can update the catalog with the following command::

  python setup.py update_catalog


.. _`Internationalization and Localization`: http://wiki.pylonshq.com/display/pylonsdocs/Internationalization+and+Localization
.. _UserGuide: http://babel.edgewall.org/wiki/Documentation/index.html
