TurboGears 2 at a glance
========================

:Status: Work in progress

TurboGears 2, like TurboGears 1 and many other modern web frameworks, uses a pattern called "Model View Controller", or "MVC" pattern.  Basically the MVC pattern is an attempt to separate the code which handles what the user sees (the view) from the code that responds to user actions (the controller) and code that changes the state of data (the model). 

The goal of the MVC pattern is to help you create more flexible software, and since web-applications tend to have more user-interface changes than anything else, it's particularly designed so that you can change the `view` code without necessarily having to change anything else. 

You have to follow the tutorial `Quickstart a TurboGears 2 Project <QuickStart.html>`_ and serve the project first.
Then we could exam some basic moves the you could do with TurboGears 2.


Hello World using template
--------------------------

Let's take advantage of that fact and make update our view with a Hello World headline. 

To keep the tutorial small and simple, we make a assumption that you already have some knowledge about html tags.

Edit helloworld/templates/index.html, add a <h1> tag like this:

.. code-block:: html

  ...
  <body>
  <h1>Hello World</h1>
  </body>
  ...

Of course you should add <h1> tag somewhere in the body of the template, to make the template as a valid HTML file.

You can now point your browser at http://localhost:8080 to see the change. You should see "Hello, world!" text in h1 size.


Hello World using static file
--------------------------------

Open a new file, edit the content as a simple html file:

.. code-block:: html

    <html>
    <body>
    <h1>Hello World</h1>
    </body>
    </html>

and save it to helloworld/public/hello.html.

Browse http://localhost:8080/hello.html and see the page.


Hello World using controller
-------------------------------

The controller defines how the server responds to user actions.   In the case of a web framework this almost always means HTTP requests of some kind (either directly initiated, or fired of by javascript as part of an Ajax app).   

TurboGears 2 uses an `Object Publishing` system to determine what controller method will be called for a particular URL.  Basically you have RootController, with @exposed objects which define your URL hierarchy. This means that the index method of your RootController is called when you go to /index (or even just /).  We can tell our controller to respond at a new URL by defining a new method. 

In this case we will add a new method called hello, which just returns a string.   TG2 allows us to bypass the template process and return a string directly to the http response, which will be returned to the browser directly.  

Edit controller/root.py:

.. code-block:: python

  from my-project-name.lib.base import BaseController
  from tg import expose

  class RootController(BaseController):

      ### skipped index method goes here!

      @expose()
      def hello(self):
          return "Hello World from the controller"

Browse http://localhost:8080/hello to see the change.


Hello World combines template with controller
-----------------------------------------------

So far we're getting somewhere, we've been returning plain text for every incoming request. But you might have noticed how the default welcome page work. 

We can edit index template, use controllers to define new url's. But let's take it one step further and create yet another new URL, plug plug real templates into the controllers, and this time rather than returning a string, we'll return a dictionary:

.. code-block:: python

  from helloworld.lib.base import BaseController
  from tg import expose

  class RootController(BaseController):

      ### skipped index and hello methods go here!

      @expose('helloworld.templates.index')
      def new_hello(self):
          return dict(hello="Hello World via template replacement")


TurboGears sees that the controller returned a dict, and that there's an template name defined in the @expose decorator, and renders that template, turning the elements of the dictionary into local variables in the template's namespace.

For each page on your site, you could give each of them the corresponding template in your controllers. You could specifying the template argument with``@expose`` decorator.

That means that we've now got a 'hello' variable in our template which we can use, and we attach the template 'helloworld.templates.index' to 'new_hello' method. So let's edit helloworld/template/index.html to replace the h1 tag we 
added earlier with:

.. code-block:: html

  <h1 py:replace="hello">hello</h1>

Browse http://localhost:8080 to see the change.

TurboGears 2 uses the Genshi templating system by deault for controlling dynamic content in your markup.
Template arguments are used to pass variables and other dynamic content to the template.

To create more skeletons for your templates, just copy the default index.html template that was generated when your project was created.


Not every template has dynamic content and therefore may not need arguments. In that case, just return an empty dictionary:

.. code-block:: python

  @expose(template="helloworld.templates.index")
  def index(self):
      return dict()

Oops, we made a mistake!  We're trying to use variables in index.html
which we're not creating in our controller. But, let's take advantage of 
this mistake to take a quick look at the interactive debugger page that 
TG2 gives you when you get a python exception in your code. 

TODO: Insert screenshot here. 
  
This gives you an opportunity to explore the full stack trace interactively.  If you click on the little + icon, you can see what local variables are set at that frame in the call stack, and you can even use the >>> prompt to type in some python code to test what's happening at that level. 

In this case, we can see that there are some issues with....


Hello World using flash
--------------------------------

Edit controller/root.py. Change the 'flash' statement to::

  flash("Hello World")

Browse http://localhost:8080 to see the change.



