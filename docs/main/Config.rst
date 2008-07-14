TurboGears 2 Configuration:
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


Our hope is that 90% of applications don't need to edit any of the config 
files, but for those who do, the most common file to change is 
``app_config.py`` 

.. code:: Wiki-20/wiki20/config/app_config.py
    :language: python 
    
Basically this sets up a base_config object, that also looks and acts like 
a dictionary.  AppConfig() is a simple class in the tg framework that provides
a set of sane default values for that object.   Any attributes you add or update
will be automatically changed in the underlying dictionary.  This base_config
object will be merged in with the config values from the .ini file you're using
to launch your app, and stuck in pylons.config. 

Setting up the base_configuration for your app
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


Embedding a TG app inside another TG app
-------------------------------------------------

There's one additional tiwhere you're placing one tg app inside of another, 
you'll need to create your own base_config like object to use when configuring 
the inside app. This can be as simple as creating your own base_config object 
from AppConfig() and 

