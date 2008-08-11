Writing controller methods
===========================

The nerve center of your TurboGears application  is **the controller**. It 
ultimately handles all user actions, because every HTTP requests arrive here 
first. The controller acts on the request and can call upon other TurboGears 
components (the template engines, database layers, etc.) as its logic directs.

When the TurboGears server receives an HTTP request, the requested URL is mapped
as a call to your controller code located in ``controllers.py``. Page names map 
to functions within the controller class.

For example:

================================== ======================
URL                                Maps to
================================== ======================
``http://localhost:8080/index``    ``Root.index()``
``http://localhost:8080/mypage``   ``Root.mypage()``
================================== ======================


Quick Example 
-------------

Suppose using ``tg-admin quickstart`` you generate a TurboGears project named
"HelloWorld". Your default controller code would be created in the file
``HelloWorld/helloworld/controllers/root.py``.

Modify the default ``controllers.py`` to read as follows:

.. code-block:: python
    
    """Main Controller"""
    from helloworld.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    #from tg import redirect, validate
    #from helloworld.model import DBSession

    class RootController(BaseController):

         @expose() 
         def index(self):
             return "<h1>Hello World</h1>"

         @expose() 
         def default(self, *args, **kw):
             return "This page is not ready"


When you load the root URL ``http://localhost:8080/index`` in your web 
browser, you'll see a page with the message "Hello World" on it. In 
addition, any of `these URLs`_ will return the same result.


Implementing a Catch-All URL via the ``default()`` Method
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

URLs not explicitly mapped to other methods of the controller will generally be 
directed to the method named ``default()``. With the above example, requesting
any URL besides ``/index``, for example ``http://localhost:8080/hello``, will 
return the message "This page is not ready". 


Adding More Pages 
~~~~~~~~~~~~~~~~~

When you are ready to add another page to your site, for example at the URL

   ``http://localhost:8080/anotherpage``

add another method to class RootController as follows::

    @expose() 
    def anotherpage(self): 
        return "<h1>There are more pages in my website</h1>"

Now, the URL ``/anotherpage`` will return:

**There are more pages in my website**


Line by Line Explanation 
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    """Main Controller"""
    from helloworld.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    #from tg import redirect, validate
    #from helloworld.model import DBSession

First you need to import the required modules. 

There's a lot going on here, including some stuff for internationalization.  
But we're going to gloss over some of that for now.  The key thing to notice is 
that you are importing a BaseController, which your RootController must inherit 
from.   If you're particularly astute, you'll have notice that you import this 
BaseController from the lib module of your own project, and not from TurboGears. 

TurboGears provides a base TGController, but it's imported in lib folder of current project (HelloWorld/helloworld/lib). 
So that you can modify it to suit the needs of your application. For example you
can define actions which will happen on every request, add parameters
to every template call, and otherwise do what you need to the request on the way
in, and on the way out. 

The next thing to notice is that we are importing `expose` from `tg`.  
`BaseController`` classes and the expose decorator are the basis of TurboGears 
controllers.   The `@expose` decorator declairs that your method should be 
*exposed to the web*, and provides you with the ability to say how the results 
of the controller should be rendered.

The other imports are there incase you do the internationalization,
or use the HTTP redirect function, validate inputs/outputs, or use the models.

::

    class RootController(BaseController):

``RootController`` is the required standard name for the RootController class of a TurboGears application and it should be inherited from 
``BaseController`` class. It is thereby specified as the request handler class 
for the website's root. 

In TurboGears 2 the web site is represented by a tree of controller objects 
and their methods, and a TurboGears website always grows out from the ``Root`` 
class.

::

    def index(self): 
        return "<h1>Hello World</h1>"

.. _these urls: 
.. _three urls:

We look at the methods of the ``Root`` class next.

The ``index`` method is the start point of any TurboGears controller class. When
you access a URL like

* http://localhost:8080 
* http://localhost:8080/ 
* http://localhost:8080/index 

they are all mapped to the ``RootController.index()`` method.

If a URL is requested and does not map to a specific method, the
``default()`` method of the controller class is called::

    def default(self):  
        return "This page is not ready"


In this example, all pages except the `three URLs`_ listed above will map to the
default method. 

As you can see from the examples, the response to a given URL is determined by
the method it maps to.

::

    @expose()

The ``@expose()`` seen before each controller method directs TurboGears controllers to make
the method accessible through the web server. Methods in the controller class
that are *not* "exposed" can not be called directly by requesting a URL from the
server.

There is much more to @expose(). It will be our access to TurboGears'
sophisticated rendering features that we will explore shortly.

Are you sure you wanted to ``expose`` strings all the time?
------------------------------------------------------------

As shown above, controller methods return the data of your website. So far, we
have returned this data as literal strings. You could produce a whole site by
returning only strings containing raw HTML from your controller methods, but it
would be difficult to maintain, since Python code and HTML code would not be
cleanly separated.


Expose + Template == Good 
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To enable a cleaner solution, data from your TurboGears controller can be
returned as strings, **or** as a dictionary.

With ``@expose()``, a dictionary can be passed from the controller to a template
which fills in its placeholder keys with the dictionary values and then returns 
the filled template output to the browser.

Template Example
~~~~~~~~~~~~~~~~~~~~~~~~

A simple template file called ``sample`` could be made like
this::

    <html> 
      <head>
	<title>TurboGears Templating Example</title>
      </head> 
      <body>
          <h2>I just want to say that ${person} should be the next
            ${office} of the United States.</h2>
      </body>
    </html>

The ``${param}`` syntax in template means there's some undetermined values need to be filled.

We did that by adding a method to the controller like this ...

::

    @expose(template="helloworld.templates.sample")
    def example(self): 
        mydata = {'person':'Tony Blair','office':'President'}
        return mydata

... the following is made possible:

* The web user goes to ``http://localhost:8080/example``.
* The ``example`` method is called. 
* The method ``example`` returns a Python ``dict``.
* @expose processes the dict through the template file named 
  ``sample.html``. 
* The dict values are substituted into the final web response.
* The web user sees a marked up page saying:

The result is::

  **I just want to say that Tony Blair should be the next President of the United States.**

Template files can thus house all markup information, maintaining clean
separation from controller code.

SubControllers and the URL Hierarcy
-----------------------------------

Sometimes your web-app needs a URL structure that's more than one level deep. 

TurboGears provides for this by traversing the object hierarchy, to find 
a method that can handle your request. 

To make a sub-controller, all you need to do is make your sub-controller 
inherit from the object class.  However there's a SubController class ``Controller`` in 
your project's lib.base (HelloWorld/helloworld/lib/base.py) for you to use if you want a central place to add helper methods or other functionality to your SubControllers::

    from lib.base import BaseController, Controller
    from tg import redirect

    class MovieController(Controller):
        @expose()
        def index(self):
            redirect('list/')

        @expose()
        def list(self):
            return 'hello'

    class RootController(BaseController):
        movie = MovieController()

Once you've done, you can follow the link: 

* http://localhost:8080/movie/ 
* http://localhost:8080/movie/index

and you will be redirected to:

* http://localhost:8080/movie/list/

Unlike turbogears 1, going to http://localhost:8080/movie **will not** redirect 
you to http://localhost:8080/movie/list.  This is due to some interesting bit 
about the way WSGI works.   But it's also the right thing to do from the 
perspective of URL joins.  Because you didn't have a trailing slash, there's no 
way to know you meant to be in the movie directory, so redirection to relative 
URL's will be based on the last / in the URL.  In this case the root of the site. 

It's easy enough to get around this, all you have to do is write your redirect 
like this::

    redirect('/movie/list/')

Which provides the redirect method with an absolute path, and takes you 
exactly where you wanted to go, no matter where you came from. 

Passing Arguments to the Controller 
---------------------------------------

HTTP GET request will have the query parameters turned into a dictionary, 
which is then turned into keyword arguments passed into your controller
methods. Likewise HTTP POST requests will have the form arguments turned 
into a dictionary which is similarly turned into parameter values 
passed into your controller. 

When you got the parameters, those parameters are in plain string format.
You should translate those plain strings to some useful format(type) for further process.
TurboGears helps you to translate and validate those parameters by ``validate`` module and  widget framework. But it's the another topic.


What's new in TG2
--------------------

Here are the major differences in dispatch between CherryPy/Turbogears1 
and TurboGears 2.

* We have not yet implemented cherrypy's mechanism that replaces dots in the 
  URL with underscores when looking up a method name.  If this feature is 
  important to you let us know on the mailing list. 

* TurboGears2 implements a Quixote inspired lookup method which allows you to do 
  customized dispatch at any time.

* Redirect does not know "where you are" in the object tree and move you on 
  from there, it just joins the URL the user requested, with the absolute
  or relative URL you provide.   Using absolute URLs is recommended. 

The new TG2 Lookup Method
--------------------------

``Lookup`` and ``default`` are called in identical situations: when "normal"
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

The benefit over "default" handlers is that you *return* an object that acts 
as a sub-controller and continue traversing rather than *being* a controller 
and stopping traversal altogether.  This allows you to use actual objects with 
data in your controllers. 

Plus, it makes RESTful URLs much easier than they were in TurboGears 1.
