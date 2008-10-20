## Please see the page "DocHelp" for guidelines on contributing TurboGears documentation!


mod_wsgi
==========

:Status: stub 

mod_wsgi site documents how to use virtualenv:

http://code.google.com/p/modwsgi/wiki/VirtualEnvironments

You can then deploy your TG2 app as described here:

http://code.google.com/p/modwsgi/wiki/IntegrationWithPylons

But you will want to make sure that the TG controllers are loaded up even before the first request comes in, so you should add this::

  import paste.fixture
  app = paste.fixture.TestApp(application)
  app.get("/")

to the end of the wsgi-script that starts your application.  This will fetch the index page of your app, thus assuring that it's ready to handle all of your requests immediately.  

This avoids a problem where your controllers are not loaded so widgets aren't initialized, but a request comes in for a widget resource and the ToscaWidgets middleware isn't aware of the widget's existence yet. 

