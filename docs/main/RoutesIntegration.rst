

Routes Integration in TG2
==========================

:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2

TurboGears2 does URL dispatch with a combination of TG1 style object dispatch, and built in Routes integration.  By default you don't 
need to think about Routes at all, because the framework sets up a default route to your RootController, which sees that the action is route, and does object dispatch in the same way that TurboGears 1 did.  

But if you want to create special routes that overide Object Dispatch, you can easily do that, just by providing your own function to setup the routes map.  TurboGears has a setup module, which provides a make_default_route_map function like this ::

  from pylons import config
  from routes import Mapper

  def make_default_route_map():
      """Create, configure and return the routes Mapper"""
      map = Mapper(directory=config['pylons.paths']['controllers'],
                  always_scan=config['debug'])
                
      ## Replace the next line with your overides.   Overides should generally come
      ## before the default route defined below
      # map.connect('overide/url/here', controller='mycontrller', action='send_stuff')
    
      # This route connects your root controller
      map.connect('*url', controller='root', action='route')

      return map

There's a single map.connect() call which sets up all urls (via the * wildcard) assigns them to the URL param, and sends them to the RootController in the root.py file in your project's controllers folder.  The default environment.py file in your config directory takes this and assigns it to make_map, which is passed in as a configuration element to the RoutesMiddleware setup in middleware.py.::

    # This setups up a set of default route that enables a standard
    # TG2 style object dispatch.   Fell free to overide it with 
    # custom routes.
    
    make_map = setup.make_default_route_map

To define your own custom routes, all you need to do is to replace this with your own make_map implementation.  If you want you can set up object dispatch from places other than root.py, or even use routes to define all of your URLs. If you are going to do object dispatch, make sure the controller that you dispatch too inherits from TGController, since that's the controller that knows how to do internal dispatch. 
 
For more information about how to write routes, you might want to read:

http://routes.groovie.org/manual.html


