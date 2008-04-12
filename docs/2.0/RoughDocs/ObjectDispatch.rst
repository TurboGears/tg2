

Designing the URL interface
================================

:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2

TurboGears 2 has CherryPy-style object dispatch built into the BaseController itself
so when you setup a new application, the your root controller must be a BaseController.
Like CherryPy and TurboGears 1, TurboGears 2 looks up URL's based on looking up callables
in an object tree.   See, http://docs.turbogears.org/1.0/GettingStarted/CherryPy 
for a more detailed explanation of how all this works.   
The basics from that page will eventually be added here, but for now here are the major new dispatch features in TurboGears 2.

* We have not yet implemented cherrypy's mechanism that replaces dots in the URL with underscores when looking up a method name.  If this feature is important to you let us know on the mailing list. 

* TurboGears2 implements a Quxote inspired lookup method which allows you to do customized dispatch at any time. 

Lookup and default are called in identical situations: when "normal"
object traversal is not able to find an exposed method, it begins
popping the stack of "not found" handlers.  If the handler is a
"default" method, it is called with the rest of the path as positional
parameters passed into the default method.   

The not found handler stack can also contain "lookup" methods, which
are different, as they are not actual controllers. 

A lookup method takes as its argument the remaining path elements and
returns an object (representing the next step in the traversal) and a
(possibly modified) list of remaining path elements.  So a blog might
have controllers that look something like this::

  class BlogController(BaseController):

     @expose()
     def lookup(self, year, month, day, id, *remainder):
        dt = date(int(year), int(month), int(day))
        blog_entry = BlogEntryController(dt, int(id))
        return blog_entry, remainder

  class BlogEntryController(object):
     
     def __init__(self, dt, id):
         self.entry = model.BlogEntry.get_by(date=dt, id=id)
     
     @expose(...)
     def index(self):
        ...
     @expose(...)
     def edit(self):
         ...
     
     @expose()
     def update(self):
        ....


So a URL request to .../2007/6/28/0/edit would map first to the 
BlogController's lookup method, which would lookup the date, instantiate 
a new BlogEntryController object (blog_entry), and pass that blog_entry object 
back to the object dispatcher,  which uses the remainder do continue dispatch, 
finding the edit method. And of course the edit method would have access to self.entry, 
which was looked up and saved in the object along the way. 


In other situations, 
you might have a several-layers-deep "lookup" chain, e.g. for 
editing hierarchical data (/client/1/project/2/task/3/edit).  

The benefit over "default" handlers is that you _return_ an object that acts as a sub-controller and continue traversing rather than _being_ a controller and 
stopping traversal altogether.  This allows you to use actual objects with data
in your controllers. 

Plus, it makes RESTful URLs much easier than they were in TurboGears 1.



