

Using PyAMF with TurboGears2
==============================

:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2

PyAMF provides a simple way to talk to Flex applications using the binary AMF protocol.   The main advantages of AMF are that it:

 #. Provides native Flash Actionscript representations of your data, so instantiating it on the client side is almost instantaneous.  
 #. Is understood by the RemoteObject in Flex, so it is very easy to implement remote procedure calls from the Flex client.

PyAMF provides serialization of a variety of native python types, from strings, lists, and dictionaries to datetime objects, elementtree elements, and custom classes.  And a lot of this is automatic, and very cool.  Return a dictionary form you pyamf service, and you'll get an Actionscript hash/object on the other side.

PyAMF provides a simple WSGI Application that can be used to setup RPC style service easily in Python.   And because TG2 supports WSGI from top-to-bottom, it's very simple to setup a TG2 app that contains web-services for your flex applications.  All you need to do is:

 #. Install a bunch of stuff and setup a TG2 app
 #. Create a PyAMF gateway for your services
 #. Create a custom route to mount your services in your TG2 app
 #. Build a Flex client that consumes those services
 #. ...
 #. Profit

Installing Stuff:
----------------------

If you haven't installed TG2, you'll need to do that first (http:docs.turbogears.org/2.0/RoughDocs/DownloadInstall).  You'll need TG2 version that's newer than Febuary 20, 2007 for this to work.  All released versions of TG2 should work, but early SVN versions may need to be updated.  Once you've got an up-to-date version of TG2,  you'll need to install PyAMF, which you can do by::

  easy_install pyamf

After that's done, you can create a new TG2 project in the normal way ::

  paster quickstart pyamftest
  ...
  cd pyamftest
  paster serve development.ini --reload

Your project should now be started, and you should be able to browse to it at http://127.0.0.1:8080

Creating the PyAMF gateway:
----------------------------

Now, you're ready to start creating a PyAMF gateway for your Flex app.  The first thing to do is to create a new gateway.py file in pyamftest/pyamftest/controllers When you've got that file created, add the following contents::

 from pyamf.remoting.gateway.wsgi import WSGIGateway

 def echo(data):
     return "Turbogears gateway says:" + str(data)
  
 def sum(a, b):
     return a + b

 def scramble(text):
     from random import shuffle
     s = [x for x in text]
     shuffle(s)
     return ''.join(s)
   
 # Expose our services:
 services = {
     'echo': echo,
     'sum': sum,
     'scramble': scramble
 }

 GatewayController = WSGIGateway(services)

This sets up a GatewayController WSGI app that has three services that can be called from flex: echo, sum, and scramble, which each do exactly what they say they do. 

Setup a Route to your services:
-----------------------------------

Now that we have a service, we can modify pyamftest/pyamftest/config/environment.py to have a route to the GatewayController. 

This requires creating a custom overide for the standard TG2 object dispatch.  See http://docs.turbogears.org/2.0/RoutesIntegration for more information. 

Basically you need to set up custom route_map function, that has a map.connect() function which sets a link up the URL you want to use for your service, and  and the WSGI controller you want to call for that URL::

  map.connect('gateway', controller = 'gateway')

If you want to you can just copy and paste this in as a replacement for your environment.py file::

    """TurboGears environment configuration"""
    import os

    from pylons import config

    from pylons.i18n import ugettext
    from genshi.filters import Translator
    from tg import setup
    from sqlalchemy import engine_from_config

    import pyamftest.lib.app_globals as app_globals

    from routes import Mapper  ##### Add this line #########

    def make_map():
        """Create, configure and return the routes Mapper"""
        map = Mapper(directory=config['pylons.paths']['controllers'],
                     always_scan=config['debug'])
   
        # This route connects your root controller
        map.connect('gateway', controller = 'gateway')  ####### Add this line ########
        map.connect('*url', controller='root', action='route')
   
        # The ErrorController route (handles 404/500 error pages); it should
        # likely stay at the top, ensuring it can always be resolved
        map.connect('error/:action/:id', controller='error')

        # CUSTOM ROUTES HERE
        # map.connect(':controller/:action/:id')
        map.connect('*url', controller='template', action='view')

        return map

    def template_loaded(template):
        "Plug-in our i18n function to Genshi."
        template.filters.insert(0, Translator(ugettext))

    def load_environment(global_conf, app_conf):
        """Configure the Pylons environment via the ``pylons.config``
        object
        """
        # Pylons paths
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        paths = dict(root=root,
                     controllers=os.path.join(root, 'controllers'),
                     static_files=os.path.join(root, 'public'),
                     templates=[os.path.join(root, 'templates')])
   
        # This setups up a set of default route that enables a standard
        # TG2 style object dispatch.   Fell free to overide it with
        # custom routes.  TODO: Link to TG2+routes doc.
       
        # Initialize config with the basic options
        config.init_app(global_conf, app_conf, package='pyamftest',
                        template_engine='genshi', paths=paths)
        config['routes.map'] = make_map()               
        config['pylons.g'] = app_globals.Globals()
        config['pylons.g'].sa_engine = engine_from_config(config, 'sqlalchemy.')

        # Customize templating options via this variable
        tmpl_options = config['buffet.template_options']
        tmpl_options['genshi.loader_callback'] = template_loaded

        # CONFIGURATION OPTIONS HERE (note: all config options will override
        # any Pylons config options)

        from pyamftest import model
        model.DBSession.configure(bind=config['pylons.g'].sa_engine)
        model.metadata.bind = config['pylons.g'].sa_engine
   
Create a Flex Client
----------------------

Now we're ready for the big time event, we can create a brand new Flex client which talks to our TG2 hosted PyAMF services. This little tutorial pretty much assumes that you know how to use Flex and just want to see how to connect it to a TurboGears app.   If that's not the case you may want to run through one of the Flex tutorials before you try this next step. 

Here's the MXML::

    <?xml version="1.0" encoding="utf-8"?>
    <mx:WindowedApplication xmlns:mx="http://www.adobe.com/2006/mxml" horizontalAlign="left">
    <mx:RemoteObject id="remoteObj" endpoint="http://127.0.0.1:8080/gateway" destination="Services"
        result="displayResult(event)" fault="remoteFault(event)">
        <mx:method name="scramble" result="scrambleResult(event)"/>
    </mx:RemoteObject>
    <mx:Button click="remoteObj.echo('Hello, There!')" label="Hello"/>
    <mx:HBox width="100%">
        <mx:Button click="remoteObj.sum(new Number(a.text), new Number(b.text))" label="Sum"/>
        <mx:TextInput id="a" text="47"/>
        <mx:TextInput id="b" text="99"/>
    </mx:HBox>
    <mx:HBox width="100%">
        <mx:Button click="remoteObj.scramble(c.text)" label="Scramble"/>
        <mx:TextInput id="c" text="She sells seashells by the seashore" width="100%"/>
    </mx:HBox>
    <mx:Text id="result" width="100%" height="100%"/>

    <mx:Script>
    <![CDATA[
    import mx.utils.ObjectUtil;
    import mx.rpc.events.ResultEvent;
    import mx.rpc.events.FaultEvent;

    private function displayResult(re:ResultEvent): void {
        result.text += ObjectUtil.toString(re.result) + "\n";
    }

    private function scrambleResult(re:ResultEvent): void {
        c.text = re.result as String;
    }

    private function remoteFault(fault:FaultEvent): void {
        result.text = ObjectUtil.toString(fault);
    }
    ]]>
    </mx:Script>
    </mx:WindowedApplication>

You can paste that into a new Flex Builder project (or use the free SDK to create a project with the text editor of your choice).  You can then put the HTML and SWF files generated by the builder into your TG2 project's static directiory (wherever you want them to be available) at which point you should be able to browse there, get your Flex app, and use it to connect to the web services you just created. 
 


