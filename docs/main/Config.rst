TurboGears 2 Configuration
===================================

Like TurboGears 1, the application configuration is separated from the 
deployment specific information.  In TG2 there is a config module, containing 
several configuration specific python files -- these are done in python not
as INI files, because they actually setup the TG2 application, it's associated
WSGI middleware.  Besides which, these files are not intended to be edited by
application end-users.
   
All of this is similar to Pylons, but we've tried to make the configuration
as declarative as possible, and to move some of the code into the framework
to make end-user updates easier to process. 

The config module
____________________________________

.. tip::
    A good indicator of whether an option should be set in the ``config`` directory code vs. the configuration file is whether or not the option is necessary for the functioning of the application. If the application won't function without the setting, it belongs in the appropriate :file:`config/` directory file. If the option should be changed depending on deployment, it belongs in the :ref:`run-config`.


Our hope is that 90% of applications don't need to edit any of the config module
files, but for those who do, the most common file to change is 
``app_config.py`` 

.. code:: Wiki-20/wiki20/config/app_cfg.py
    :revision: 4842
    :language: python
    
app_cfg.py exists primarily so that middleware.py and environment'py can import 
and use the base_config object.  The base_config object 
is special in that it transparently maps all attribute access to an underlying 
dictionary.  AppConfig() is a simple class in the tg framework that provides
a set of sane default values for the base_config object.   

Any attributes you add or update will be automatically changed in the 
underlying dictionary.  If you'd prefer not t use this feature, you can just 
treat it like a dictionary.   Ultimately, This base_config
object will be merged in with the config values from the .ini file you're using
to launch your app, and stuck in pylons.config. 

In addition to the attributes on the base_config object there are a number of 
methods which are used to setup the environment for you application, and to 
create the actual turbogears WSGI application, and all the middleware you need.

You can override these methods to further customize you application, for various
advanced use cases, like adding custom middleware at arbitrary points in the 
wsgi stack, or doing some unanticipated (by us) application environment 
manipulation. 

Setting up the base configuration for your app
-------------------------------------------------

The most common configuration change you'll likely want to make here is to add 
a second template engine or change the template engine used by your project. 

By default TurboGears sets up the Genshi engine, but we also provide out of 
the box support for Mako and Jinja.   To tell TG to prepare these template 
engines for you all you need to do is append 'mako' or 'jinja' to the 
renderer's list here in app_config. 

To change the default renderer to something other than Genshi, just set the 
default_renderer to the name of the rendering engine.  So, to add Mako to list
of renderers to prepare, and set it to be the default, this is all you'd have
to do: 

base_config.default_renderer = 'mako'
base_config.renderers.append('mako')

Configuration in the INI files
-------------------------------------------------

A turbogears quickstarted project will contain a couple of  .ini files which
are used to define what WSGI app ought to be run, and to store end-user 
created configuration values, which is just another way of saying that the 
.ini files should contain \deployment specific\ options.

By default TurboGears provides a development.ini, test.ini, and production.ini
files.   These are standard ini file formats. 

Let's take a closer look at the development.ini file:

.. code:: Wiki-20/development.ini
    :revision: 4842
    :language: python

These files are standard INI files, as used by Paste Deploy.   This means that      

.. seealso::
        Configuration file format **and options** are described in great 
        detail in the `Paste Deploy documentation 
        <http://pythonpaste.org/deploy/>`_.




Embedding a TG app inside another TG app
-------------------------------------------------

One place where you'll have to be aware of how all of this works is when 
you programatically setup one TurboGears app inside another. 

In that case, you'll need to create your own base_config like object to use
 when configuring the inside wsgi application instance. 
 
Fortunately, this can be as simple as creating your own base_config object 
from AppConfig(), creating your own app_conf and global dictionaries, and 
calling m


