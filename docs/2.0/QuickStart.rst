Quickstarting a TurboGears 2 project
====================================

:Status: Work in progres


Once you've got TurboGears 2 installed, you probably want to try it out. To 
make setting up a new project very quick, TurboGears 2 extends the 'paster' 
command line tool to provide a suite of tools for working with TurboGears 2 
projects. A few will be touched upon in this tutorial, check the 'paster --help'
command for a full listing.

The first paster tool you'll need is 'quickstart', which initializes a 
TurboGears 2 project.

To use it go to whatever directory you want your project to be in, and type::

  $ paster quickstart Helloworld

The 'paster quickstart' command will create a basic project directory for you to 
use to get started on your TurboGears 2 application. You'll be prompted for the 
name of the project (this is the pretty name that human beings would appreciate),
and the name of the package (this is the less-pretty name that Python will like).

For the identity prompt, answer 'no' (or press 'Enter' key directly), since we'll keep this tutorial fairly simple, but when you need users/passwords in a future project, you'll want to look up the identity management tutorial.

Here's what our choices for this tutorial look like::

    Enter project name: Helloworld
    Enter package name [helloworld]: helloworld
    Do you need Identity (usernames/passwords) in this project? [no]
    ...output...

This will create a new directory which contains a few files in a directory tree,
with some code already set up for you.

Let's go in there and you can take a look around::

  $ cd helloworld

.. note:: you could type following command to check the full quickstart capabilities::

  $ paster quickstart --help

Run the server
---------------

At this point your project should be operational. To start your new TurboGears 2
app, cd into the new directory ( helloworld ) and issue the second paster 
command 'paster serve' to serve your new application::

  $ paster serve development.ini

As soon as that's done. Point your browser at http://localhost:8080/, and 
you'll see a nice welcome page with the inform(flash) message and current time.

.. note::

  If you're exploring TurboGears 2 after using TurboGears 1, you may notice that 
  the old config file `dev.cfg` file is now `development.ini`.

Reload the server automatically
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Also note that by default 'paster serve' is *not* in auto-reload mode.

If you want your application to auto-reload whenever you change a 
source code file as was the default in a TurboGears 1's dev.fg, just add 
a `--reload` option.  So, to get reloading you'd just type this instead::

  $ paster serve --reload development.ini

Then you could access http://localhost:8080 to view the running TurboGears app.

.. note:: you could type following command to check the full quickstart capabilities::

  $ paster serve --help

Glancing the Source
--------------------

If you take a look at the code that quickstart created, you'll see that 
there isn't much involved in getting up and running.

In particular, you'll want to check out the files directly involved in 
displaying this welcome page:

  * development.ini : The system configuration is laid on development.ini 
    for development configuration
  * helloworld/controllers/root.py : The python file is responsible to generate the welcome page.
  * helloworld/templates/index.html : The html template is the template you
    view on the welcome screen. It's an standard XHTML with some simple
    namespaced attributes. 
    You can even preview it directly by open it in your browser! Very 
    designer-friendly.
  * helloworld/public/ : The place to hold static files, such as pictures, 
    javascript, or css files.

Change the server port
~~~~~~~~~~~~~~~~~~~~~~~

You could edit development.ini to change the default server port used by the 
built-in web server::

  [server:main]
  ...
  port = 8080



