

Routes Integration in TG2
==========================

:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2

TurboGears2 does URL dispatch with a combination of TG1 style object dispatch, 
and built in Routes integration.  By default you don't need to think about 
Routes at all, because the framework sets up a default route to your 
RootController, which sees that the action is route, and does object 
dispatch in the same way that TurboGears 1 did.  

But if you want to create special routes that overide Object Dispatch, 
you can easily do that, just by providing your own function to setup the 
routes map. You can update the routes defaults by overriding the setup_routes
method of the base_config object in app_cfg.py.  

The standard setup_routes method looks like this::

    def setup_routes(self):
        """Setup the default TG2 routes
    
        Overide this and setup your own routes maps if you want to use routes.
        """
        map = Mapper(directory=config['pylons.paths']['controllers'],
                    always_scan=config['debug'])

        # Setup a default route for the error controller:
        map.connect('error/:action/:id', controller='error')
        # Setup a default route for the root of object dispatch
        map.connect('*url', controller='root', action='routes_placeholder')
    
        config['routes.map'] = map
    

There's a single map.connect() call which sets up all urls (via the * 
wildcard) assigns them to the URL param, and sends them to the 
RootController in the root.py file in your project's controllers folder.
When TurboGears loads the environment for your app, it will use this 
setup_routes method to do it.   

So to create your own routes, all you need to do is create another map.connect
call above the `*url` call that connects you to the root controller. 

If you want to start object dispatch from a different root than '/' all you 
need to do is change the `'*url'` line to mount something somewhere else. 

If you have a very large app, and you want to break down the object dispatch 
tree for performance reasons, you can do that by defining routes to 
objects further down the tree. 

For more information about how to write routes, you might want to read:

http://routes.groovie.org/manual.html


