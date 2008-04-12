

.. contents::
   :depth: 2

The TurboGears 2 Wiki Tutorial
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Welcome!  This tutorial will show you how to create a simple wiki with
TurboGears 2. It is designed to be your first experience with TurboGears 2.

If you're not familiar with wikis, you might want to check out `the
Wikipedia entry <http://en.wikipedia.org/wiki/Wiki>`_.  Basically, a
wiki is an easily-editable collaborative web content system that makes
it trivial to link to pages and create new pages.

If you have trouble with this tutorial, ask for help on
the `TurboGears discussion list`_. We're a friendly bunch and depending
what time of day you post, you'll get your answer in a few minutes to a
few hours. If you search the mailing list or the web in general, you'll
probably get your answer even faster. **Please don't post your problem
reports as comments on this or any of the following pages of the
tutorial**. Comments are for suggestions for improvement of the docs
etc., not for seeking support.

.. _TurboGears discussion list: http://groups.google.com/group/turbogears

Setup
==================

To go through this tutorial, you'll need:

#.  `Python 2.4 or 2.5 <http://www.python.org/download/>`_. Note that Mac
    OSX 10.5 (Leopard) comes with Python 2.5 preinstalled; for 10.4 and
    before, follow *Macintosh* in the above link.

#.  `TurboGears 2.0
    <DownloadInstall>`_ or higher.

#.  docutils_ 0.4 or later,
    which is used for the wiki's formatting. ``docutils`` is not a required
    part of TurboGears, but is needed for this tutorial. Install it with::

        $ easy_install docutils

    When using **easy_install**, it doesn't matter what directory you're in.
    If you don't have **easy_install**, you only need to run
    http://peak.telecommunity.com/dist/ez_setup.py from any directory.

#.  A web browser.

#.  Your favorite editor.

#.  Two command line windows
    (you only *need* one, but two is nicer).

#.  A database. Python 2.5 comes
    **sqlite**, so if you have Python 2.5, don't do anything. If you're
    running Python 2.4, your best bet is sqlite 3.2+ with `pysqlite
    <http://cheeseshop.python.org/pypi/pysqlite>`_ 2.0+. Install it with::

        $ easy_install pysqlite

#.  **Optional:** If you're not aware of it, you may also find the
    `ipython shell`_ to be helpful. It supports attribute tab completion for
    many objects (which can help you find the method you're searching for)
    and can display contextual help if you append a question mark onto the
    end of an object or method. You can do the same in the standard shell
    with the ``dir()`` and ``help()`` functions, but ipython is more
    convenient. ipython has a number of other convenient features, like
    dropping into the debugger on an error; take a look at the `ipython docs`_
    for more information. You can install it with::

        $ easy_install ipython

This tutorial doesn't cover Python at all. Check the `Python
Documentation <http://www.python.org/doc/>`_ page for more coverage of
Python.

.. _ipython shell: http://ipython.scipy.org/
.. _ipython docs: http://ipython.scipy.org/moin/Documentation
.. _docutils: http://cheeseshop.python.org/pypi/docutils


Quickstart
====================================

TurboGears provides a suite of tools for working with projects by adding
several commands to the Python command line tool ``paster``. A few will
be touched upon in this tutorial. (Check the `command line reference`_
for a full listing.) The first tool you'll need is ``quickstart``, which
initializes a TurboGears project.  Go to one of your command line
windows and run the following command::

    $ paster quickstart

.. _command line reference : http://docs.turbogears.org/2.0/CommandLine

You'll be prompted for the name of the project (this is the pretty name
that human beings would appreciate), and the name of the package (this
is the less-pretty name that Python will like). Here's what our choices
for this tutorial look like::

    $ paster quickstart
    Enter project name: Wiki 20
    Enter package name [wiki20]: wiki20

Now **paster** will spit out a bunch of stuff::

    Selected and implied templates:
      TurboGears2#turbogears2
      TurboGears 2.0 Template

    ...etc...

    running compile_catalog
    1 of 1 messages (100%) translated in 'wiki20/i18n/ru/LC_MESSAGES/wiki20.po'
    compiling catalog 'wiki20/i18n/ru/LC_MESSAGES/wiki20.po' to 'wiki20/i18n/ru/LC_MESSAGES/wiki20.mo'


This creates a few files in a directory tree just below your current
directory. Go in there and take a look around::

    $ cd Wiki-20

``paster`` provides a simple mechanism for running a TurboGears project.
From inside the ``Wiki-20`` directory, run this command::

    $ paster serve --reload development.ini

(You'll get a warning that starts with ``No handlers could be found for
logger "toscawidgets.view"``, but that's OK; your system will still
run.)

The ``--reload`` flag means that changes that you make in the project
will automatically cause the server to restart itself. This way you
immediately see the results.

Point your browser at `http://localhost:8080/`_, and you'll see a nice
little welcome page with the current time. You now have a working
project!

Controller and View
=================================

If you take a look at the code that ``quickstart`` created, you'll see
everything necessary to get up and running. Here, we'll look at the two
files directly involved in displaying this welcome page.

TurboGears follows the `Model-View-Controller paradigm`_ (a.k.a. "MVC"),
as do most modern web frameworks like Rails, Cake, Struts, etc.

*   **Model**: For a web application, the "model" refers to the way the
    data is stored. In theory, any object *can* be your model. In practice,
    since we're in a database-driven world, your model will be based on a
    relational database. By default, TurboGears 2 uses the powerful,
    flexible, and relatively easy-to-use SQLAlchemy object relational mapper
    to build your model, and to talk to your database. We'll look at this in
    a later section.

*   **View**: To minimize duplication of effort, web frameworks use
    *templating engines* which allow you to create "template" files to
    specify how a page will always look, with hooks where the templating
    engine can substitute information provided by your web application.
    TurboGears 2's default templating engine is `Genshi`_.  If you really
    love another templating engine, there are `plugins available`_ for most
    popular Python templating engines. See the `using alternate templating
    engines`_ article for details.

*   **Controller**: The controller is the way that you tell your web
    application how to respond to events that arrive on the server. In a web
    application, an "event" usually means "visiting a page" or "pressing a
    submit button," and the response to an event usually consists of
    executing some code and displaying a new page. TurboGears 2 uses its own
    simple controller.

Controller Code
-------------------------

``Wiki-20/wiki20/controllers/root.py`` is the code that causes the
welcome page to be produced. After the imports, the first line of code
creates our main controller class by inheriting from TurboGears'
``BaseController``::

    class RootController(BaseController):

The TurboGears 2 controller is a simple object publishing system; you
write controller methods and ``@expose()`` them to the web. In our case,
there's a single controller method called ``index``. As you might guess,
this name is not accidental; this becomes the default page you'll get if
you go to this URL without specifying a particular destination, just
like you'll end up at ``index.html`` on an ordinary web server if you
don't give a specific file name. You'll also go to this page if you explicitly name it,
with `http://localhost:8080/index`_. (We'll see other controller methods
later in the tutorial so this naming system will become clear).

The ``@expose()`` decorator tells TurboGears which
template to use to render the page.  Our ``@expose()`` specifies::

    @expose('wiki20.templates.index')

This gives the file name to use, including the path information (the
``.html`` extension is implied). We'll look at this file shortly.

The ``flash()`` function is a simple way to show a message.

Each controller method returns a dictionary, as you can see at the end
of ``index``. TG takes the key:value pairs in this dictionary and turns
them into local variables that can be used in the template.

Displaying the Page
---------------------------

``Wiki-20/wiki20/templates/index.html`` is the template specified by the
``@expose()`` decorator, so it formats what you view on the welcome
screen. Look at the file; you'll see that it's standard XHTML with some
simple namespaced attributes. This makes it very designer-friendly, and
well-behaved design tools will respect all the `Genshi`_ tags. You can
even open it directly in your browser.

Genshi directives are usually found within ``div`` or ``span`` tags, and
begin with the ``py:`` namespace. Each one represents a python block of
code, but instead of ending with the outdent as in python, the end of
the tag represents the end of the block. Look through the ``index.html``
file to see the Genshi directives.

.. _Model-View-Controller paradigm: http://en.wikipedia.org/wiki/Model-view-controller
.. _plugins available: http://www.turbogears.org/cogbin/
.. _Gensh: http://genshi.edgewall.org/wiki/Documentation/xml-templates.html
.. _using alternate templating engines: 1.0/AlternativeTemplating

Next, we'll set up our data model, and create a database.


Wiki Model and Database
============================================

``quickstart`` produced a directory for our model in
``Wiki-20/wiki20/model/``. This directory is empty except for the
``__init__.py`` file, which makes that directory name into a python
module (so you can say ``import model``).

In order to easily use our model within the application, modify the
``Wiki-20/wiki20/model/__init__.py`` file to add ``Page`` and ``pages_table``
to the module. Add the following line
*at the end of the file*. It's very important that this line is at the
end because of some initialization ordering issues::

    from wiki20.model.page import Page, pages_table

Since a wiki is basically a linked collection of pages, we'll define a
``Page`` class as the name of our model. Create a new file called ``page.py`` in the
``Wiki-20/wiki20/model/`` directory::

    from sqlalchemy import *
    from sqlalchemy.orm import mapper
    from wiki20.model import metadata

    # Database table definition
    # See: http://www.sqlalchemy.org/docs/04/sqlexpression.html

    pages_table = Table("pages", metadata,
        Column("id", Integer, primary_key=True),
        Column("pagename", String, unique=True),
        Column("data", String)
    )

    # Python class definition
    class Page(object):
        pass

    # Mapper
    # See: http://www.sqlalchemy.org/docs/04/mappers.html
    page_mapper = mapper(Page, pages_table)

The ``MetaData`` object is automatically created by the ``paste`` command
inside the ``__init__.py`` file. It's a "single point of truth" that keeps all the
information necessary to connect and use the database. It includes the
location of the database, connection information, and the tables that
are in that database. When you pass the metadata object to the various
objects in your project they initialize themselves using that metadata.

In this case, the metadata object configures itself using the
``Wiki-20\development.ini`` file, which we'll look at in the next
section.

The SQLAlchemy ``Table`` object defines what a single table looks like
in the database, and adds any necessary constraints (so, for example,
even if your database doesn't enforce uniqueness, SQLAlchemy will
attempt to do so). The first argument in the ``Table`` constructor is
the name of that table inside the database. Next is the aforementioned
``metadata`` object followed by the definitions for each ``Column``
object. As you can see, ``Column`` objects are defined in the same way that you
define them within a database: name, type, and constraints.

The ``Table`` object provides the representation of a database table,
but we want to just work with objects, so we create an extremely simple
class to represent our objects within TurboGears. The above idiom is
quite common: you create a very simple class like ``Page`` with nothing
in it, and add all the interesting stuff using ``mapper()``, which attaches
the ``Table`` object to our class.

Note that it's also possible to start with an existing database, but
that's a more advanced topic that we won't cover in this tutorial.

Database Configuration
----------------------

By default, projects created with ``quickstart`` are configured to use a
very simple SQLite database (however, TurboGears 2 supports most popular
databases). This configuration is controlled by the ``development.ini``
file in the root directory (``Wiki-20``, for our project).

Search down until you find the ``[app:main]`` section in
``development.ini``, and then look for ``sqlalchemy.url``. You should
see this::

    sqlalchemy.url = sqlite:///%(here)s/devdata.db

Turbogears will automatically replace the ``%(here)s`` variable with the parent directory of
this file, so for our example it will produce
``sqlite:///Wiki-20/devdata.db``. You won't see the ``devdata.db`` file now because we
haven't yet initialized the database.


Initializing the Tables
--------------------------------

Before you can use your database, you need to initialize it and add some data.
The easiest way to do this is just to run a Python script. Create a file called
**initializeDB.py** in the ``Wiki-20`` directory containing the following::

	from wiki20.model import DBSession, Page, metadata
	from sqlalchemy import create_engine

	# Prepare the database connection
	engine = create_engine("sqlite:///devdata.db", echo=True)
	DBSession.configure(bind=engine)

	# Create the tables
	metadata.drop_all(engine)
	metadata.create_all(engine)

	# Create a page object and set some data
	page = Page()
	page.pagename = "FrontPage"
	page.data = "initial data"

	# Save the page object to the in memory DBSession
	DBSession.save(page)

	# Use commit() to write all in-memory changes to the database.
	DBSession.commit()


Now run the program from the ``Wiki-20`` directory::

    $ python initializeDB.py

You'll see output, but you should not see error messages. At this point
your database is created and has some initial data in it, which you can
verify by looking at ``Wiki-20/devdata.db``. The file should exist and have
a nonzero size.

That takes care of the "M" in MVC.  Next is the "C": controllers.


Adding Controllers
=======================================

Controllers are the code that figures out which page to display, what
data to grab from the model, how to process it, and finally hands off
that processed data to a template.

``quickstart`` has already created some basic controller code for us at
``Wiki-20/wiki20/controllers/root.py``.  Here's what it looks like now::

    """Main Controller"""
    from wiki20.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    #from tg import redirect, validate
    #from wiki20.model import DBSession

    class RootController(BaseController):

        @expose('wiki20.templates.index')
        def index(self):
            from datetime import datetime
            flash(_("Your application is now running"))
            return dict(now=datetime.now())

The first thing we need to do is uncomment the line that imports ``DBSession``.

Next we must import the ``Page`` class from our
model. At the end of the ``import`` block, add this line::

    from wiki20.model.page import Page

Now we will change the template used to present the data, by changing the
``@expose`` line::

    @expose('wiki20.templates.page')

This requires us to create a new template named ``page.html`` in the
``wiki20/templates`` directory; we'll do this in the next section.

Now we must specify which page we want to see.  To do this, add a
parameter to the ``index()`` method. Change the line after the
``@expose`` decorator to::

    def index(self, pagename="FrontPage"):

This tells the ``index()`` method to accept a parameter called
``pagename``, with a default value of ``"FrontPage"``.

Now let's get that page from our data model.  Put this line in the body
of ``index``::

    page = DBSession.query(Page).filter_by(pagename=pagename).one()

This line asks the current SQLAlchemy in-memory database session object to run a query
for records with a ``pagename`` column equal to the value of the
``pagename`` parameter passed to our controller method.  The ``.one()`` method assures that there is only one returned result; normally a ``.query`` call returns a list of matching objects. We only want
one page, so we use ``.one()``.

Finally, we need to return a dictionary containing the ``page`` we just looked up.
When we say::

   return dict(page=page)

The returned ``dict`` contains a single key called ``page`` and a single value
containing the page that we looked up.

Here's the whole file after incorporating the above modifications::

    """Main Controller"""
    from wiki20.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    #from tg import redirect, validate
    from wiki20.model import DBSession
    from wiki20.model.page import Page

    class RootController(BaseController):

        @expose('wiki20.templates.page')
        def index(self, pagename="FrontPage"):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            return dict(page=page)

Now our ``index()`` method fetches a record from the database (creating
an instance of our mapped ``Page`` class along the way), and returns it
to the template within a dictionary.


Adding Views (Templates)
===============================================

``quickstart`` also created some templates for us in the
``Wiki-20/wiki20/templates`` directory: ``master.html`` and
``index.html``.  Back in our simple controller, we used ``@expose()`` to
hand off a dictionary of data to a template called
``'wiki20.templates.index'``, which corresponds to
``Wiki-20/wiki20/templates/index.html``.

Take a look at the following line in ``index.html``::

    <xi:include href="master.html" />

This tells the ``index`` template to *include* the ``master`` template.
Using includes lets you easily maintain a cohesive look and feel
throughout your site by having each page include a common master
template.

Copy ``index.html`` into a file called ``page.html``. Now modify it for
our purposes::

    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
      "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html
        xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:xi="http://www.w3.org/2001/XInclude">

    <xi:include href="master.html" />

    <head>
        <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
        <title>${page.pagename} - The TurboGears 2 Wiki</title>
    </head>

    <body>

    <div class="main_content">
    <div style="float:right; width: 10em;"> Viewing
    <span py:replace="page.pagename">Page Name Goes Here</span> <br/>
    You can return to the <a href="/">FrontPage</a>.
    </div>

    <div py:replace="page.data">Page text goes here.</div>
    <a href="/edit/${page.pagename}">Edit this page</a>
    </div>

    </body></html>

This is a basic XHTML page with three substitutions:

1.  In the ``<title>`` tag, we substitute the name of the page, using
    the ``pagename`` value of ``page``.  (Remember, ``page`` is an instance
    of our mapped ``Page`` class, which was passed in a dictionary by our
    controller.)

2.  In the second ``<div>`` element, we substitute the page
    name again with Genshi's ``py:replace``: ``<span
    py:replace="page.pagename">Page Name Goes Here</span>``

3.  In the third ``<div>``, we put in the contents of our ``page``::

        <div py:replace="page.data">Page text goes here.</div>

When you refresh the output web page you should see "initial data" displayed on the page.

Part 6: Editing pages
============================================

One of the fundamental features of a wiki is the ability to edit the page just
by clicking "Edit This Page," so we'll create a template for editing. First, make a copy of
``page.html``::

    cd wiki20/templates
    cp page.html edit.html
    cd ../..

We need to replace the content with an editing form and ensure people know this
is an editing page. Here are the changes for ``edit.html``.

#. Change the title in the header to reflect that we are editing the page::

    <head>
        <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
        <title>Editing: ${page.pagename}</title>
    </head>

    <body>

#. Change the div that displays the page::

    <div py:replace="page.data">Page text goes here.</div>

   with a div that contains a standard HTML form::

    <div>
      <form action="/save" method="post">
        <input type="hidden" name="pagename" value="${page.pagename}"/>
        <textarea name="data" py:content="page.data" rows="10" cols="60"/>
        <input type="submit" name="submit" value="Save"/>
      </form>
    </div>

Now that we have our view, we need to update our controller in order to display
the form and handle the form submission. For displaying the form, we'll add an
``edit`` method to our controller in ``Wiki-20/wiki20/controllers/root.py``. The
new ``root.py`` file looks like this, with the changes in bold:

.. parsed-literal::

    """Main Controller"""
    from wiki20.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    #from tg import redirect, validate
    from wiki20.model import DBSession
    from wiki20.model.page import Page

    class RootController(BaseController):

        @expose('wiki20.templates.page')
        def index(self, pagename="FrontPage"):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            return dict(page=page)

        **@expose(template="wiki20.templates.edit")**
        **def edit(self, pagename):**
            **page = DBSession.query(Page).filter_by(pagename=pagename).one()**
            **return dict(page=page)**

For now, the new method is identical to the ``index`` method; the only difference is that
the resulting dictionary is handed to the ``edit`` template. To see it work, go to
`http://localhost:8080/edit/FrontPage`_. However, this only works because FrontPage already
exists in our database; if you try to edit a new page with a different name it will fail, which we'll
fix in a later section.

Don't click that save button yet! We still need to write that method.

Saving our edits
============================================

When we displayed our wiki's edit form in the last section, the form's
``action`` was ``/save``.  So, we need to make a method called ``save`` in
the Root class of our controller.

However, we're also going to make another important change. Our ``index`` method
is *only* called when you either go to ``/`` or ``/index``. If you change the
``index`` method to the special method ``default``, then ``default`` will be
automatically called whenever nothing else matches. ``default`` will take the
rest of the URL and turn it into positional parameters.

Here's our new version of ``root.py`` which includes both ``default`` and ``save``:

.. parsed-literal::

    """Main Controller"""
    from wiki20.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    **from tg import redirect, validate**
    from wiki20.model import DBSession
    from wiki20.model.page import Page

    class RootController(BaseController):

        @expose('wiki20.templates.page')
        **def default(self, pagename="FrontPage"):**
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            return dict(page=page)

        @expose(template="wiki20.templates.edit")
        def edit(self, pagename):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            return dict(page=page)

        **@expose()**
        **def save(self, pagename, data, submit):**
            **page = DBSession.query(Page).filter_by(pagename=pagename).one()**
            **page.data = data**
            **DBSession.commit() # Tells database to commit changes permanently**
            **redirect("/" + pagename)**

Unlike the previous methods we've made, ``save`` just uses a plain ``@expose()``
without any template specified. That's because we're only redirecting the user
back to the viewing page.

Although the ``page.data = data`` statement tells SQLAlchemy to store the page
data in the database, nothing happens until the ``DBSession.commit()``. This
structure allows SQLAlchemy to combine many operations into a single database
transaction and thus be much more efficient. You can also call
``DBSession.flush()`` to send changes to the database, then do more work, then
``flush()`` again, before finally committing. When you do a ``commit()``, that
will flush automatically for you if you haven't flushed explicitly.

You can now make changes and save the page we were editing, just like a real
wiki.

What about WikiWords?
============================================

Our wiki doesn't yet have a way to link pages. A typical wiki will automatically
create links for *WikiWords* when it finds them  (WikiWords have also been
described as WordsSmashedTogether). This sounds like a job for a regular
expression.

Here's the new version of ``root.py``, which will be explained afterwards:

.. parsed-literal::

    """Main Controller"""
    from wiki20.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    **import tg**
    from tg import redirect, validate
    from wiki20.model import DBSession
    from wiki20.model.page import Page
    **import re**
    **from docutils.core import publish_parts**

    **wikiwords = re.compile(r"\\b([A-Z]\\w+[A-Z]+\\w+)")**

    class RootController(BaseController):

        @expose('wiki20.templates.page')
        def default(self, pagename="FrontPage"):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            **content = publish_parts(page.data, writer_name="html")['html_body']**
            **root = tg.url('/')**
            **content = wikiwords.sub(r'<a href="%s\\1">\\1</a>' % root, content)**
            **return dict(content=content, page=page)**

        @expose(template="wiki20.templates.edit")
        def edit(self, pagename):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            return dict(page=page)

        @expose()
        def save(self, pagename, data, submit):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            page.data = data
            DBSession.commit() # Tells database to commit changes permanently
            redirect("/"+pagename)

We need some additional imports, including ``re`` for regular expressions and
a method called ``publish_parts`` from ``docutils``.

A WikiWord is a word that starts with an uppercase letter, has a collection
of lowercase letters and numbers followed by another uppercase letter and
more letters and numbers. The ``wikiwords`` regular expression describes a WikiWord.

In ``default``, the new lines begin with the use of ``publish_parts``, which is
a utility that takes string input and returns a dictionary of document parts after performing
conversions; in our case, the conversion is from Restructured Text to HTML.
The input (``page.data``) is in Restructured Text format, and the output format
(specified by ``writer_name="html"``) is in HTML. Selecting the ``fragment``
part produces the document without the document title, subtitle, docinfo,
header, and footer.

You can configure TurboGears so that it doesn't live at the root of a site, so
you can combine multiple TurboGears apps on a single server. Using ``tg.url()``
creates relative links, so that your links will continue to work regardless of
how many apps you're running.

The next line rewrites the ``content`` by finding any WikiWords and substituting
hyperlinks for those WikiWords. That way when you click on a WikiWord, it will
take you to that page. The ``r'string'`` means 'raw string', one that turns off
escaping, which is mostly used in regular expression strings to prevent you from
having to double escape slashes. The substitution may look a bit weird, but is
more understandable if you recognize that the ``%s`` gets substituted with
``root``, then the substitution is done which replaces the ``\1`` with the
string matching the regex.

Note that ``default()`` is now returning a ``dict`` containing an additional
key-value pair: ``content=content``. This will not break
``wiki20.templates.page`` because that page is only looking for ``page`` in the
dictionary, however if we want to do something interesting with the new
key-value pair we'll need to edit ``wiki20.templates.page``:

.. parsed-literal::

    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
      "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html
        xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:xi="http://www.w3.org/2001/XInclude">

    <xi:include href="master.html" />

    <head>
        <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
        <title>${page.pagename} - TurboGears 2 Wiki</title>
    </head>

    <body>

    <div class="main_content">
    <div style="float:right; width: 10em;"> Viewing
    <span py:replace="page.pagename">Page Name Goes Here</span> <br/>
    You can return to the <a href="/">FrontPage</a>.
    </div>
    **<div py:replace="XML(content)">Formatted content goes here.</div>**
    <a href="/edit/${page.pagename}">Edit this page</a>
    </div>

    </body></html>

Since ``content`` comes through as XML, we can strip it off using the ``XML()``
function to produce plain text (try removing the function call to see what
happens).

To test the new version of the system, edit the data in your front page to
include a WikiWord. When the page is displayed, you'll see that it's now a link.
You probably won't be surprised to find that clicking that link produces an
error.


Hey, where's the page?
============================================

What if a Wiki page doesn't exist? We'll take a simple approach: if the page
doesn't exist, you get an edit page to use to create it.

In the ``default`` method, we'll check to see if the page exists. If it doesn't,
we'll redirect to a new ``notfound`` method. We'll add this method after the
``index`` method and before the ``edit`` method. Here are the changes we make to
the controller:

.. parsed-literal::

    """Main Controller"""
    from wiki20.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    import tg
    from tg import redirect, validate
    from wiki20.model import DBSession
    from wiki20.model.page import Page
    import re
    from docutils.core import publish_parts
    **from sqlalchemy.exceptions import InvalidRequestError**

    wikiwords = re.compile(r"\b([A-Z]\w+[A-Z]+\w+)")

    class RootController(BaseController):

        @expose('wiki20.templates.page')
        def default(self, pagename="FrontPage"):
            **try:**
                **page = DBSession.query(Page).filter_by(pagename=pagename).one()**
            **except InvalidRequestError:**
                **raise tg.redirect("notfound", pagename = pagename)**
            content = publish_parts(page.data, writer_name="html")['fragment']
            root = tg.url('/')
            content = wikiwords.sub(r'<a href="%s\1">\1</a>' % root, content)
            return dict(content=content, page=page)

        **@expose("wiki20.templates.edit")**
        **def notfound(self, pagename):**
            **page = Page(pagename=pagename, data="")**
            **DBSession.save(page)**
            **DBSession.commit()**
            **return dict(page=page)**

        @expose(template="wiki20.templates.edit")
        def edit(self, pagename):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            return dict(page=page)

        @expose()
        def save(self, pagename, data, submit):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            page.data = data
            DBSession.commit() # Tells database to commit changes permanently
            redirect("/"+pagename)

The ``default`` code changes illustrate the "better to beg forgiveness than ask
permission" pattern which is favored by most Pythonistas -- we first try to get
the page and then deal with the exception by redirecting to a method that will
make a new page.

We're also leaking a bit of our model into our controller. For a larger project,
we might create a facade in the model, but here we'll favor simplicity. Notice
that we can use the ``redirect()`` to pass parameters into the destination
method.

As for the ``notfound`` method, the first 3 lines of the method adds a row to
the page table. From there, the path is exactly the same it would be
for our ``edit`` method.

In order for the ``notfound`` method to be able to create a new ``Page`` object,
we need to add a constructor to the ``Page`` class:

.. parsed-literal::

    from sqlalchemy import *
    from sqlalchemy.orm import mapper
    from wiki20.model import metadata

    # Database table definition
    # See: http://www.sqlalchemy.org/docs/04/sqlexpression.html

    pages_table = Table("pages", metadata,
        Column("id", Integer, primary_key=True),
        Column("pagename", String, unique=True),
        Column("data", String)
    )

    # Python class definition
    class Page(object):
        **def __init__(self, pagename, data):**
            **self.pagename = pagename**
            **self.data = data**

    # Mapper
    # See: http://www.sqlalchemy.org/docs/04/mappers.html
    page_mapper = mapper(Page, pages_table)

With these changes in place, we have a fully functional wiki. Give it a try!
You should be able to create new pages now.

Adding a page list
============================================

Most wikis have a feature that lets you view an index of the pages. To add one,
we'll start with a new template, ``pagelist.html``. We'll copy ``page.html`` so
that we don't have to write the boilerplate.

::

    cd wiki20/templates
    cp page.html pagelist.html

After editing, our ``pagelist.html`` looks like:

.. parsed-literal::

    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
      "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html
        xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:xi="http://www.w3.org/2001/XInclude">

    <xi:include href="master.html" />

    <head>
        <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
        <title>Page Listing - TurboGears 2 Wiki</title>
    </head>

    <body>
    <div class="main_content">

    <h1>All Pages</h1>
    <ul>
        **<li py:for="pagename in pages">**
            **<a href="${tg.url('/' + pagename)}"**
                **py:content="pagename">Page Name Here.</a>**
        **</li>**
    </ul>
    Return to the <a href="/">FrontPage</a>.

    </div>

    </body></html>

The bolded section represents the Genshi code of interest. You can guess that
the ``py:for`` is a python ``for`` loop, modified to fit into Genshi's XML. It
iterates through each of the ``pages`` (which we'll send in via the controller,
using a modification you'll see next). For each one, ``Page Name Here`` is
replaced by ``pagename``, as is the URL. You can learn more about Genshi by
following the link at the bottom of this page.

We must also modify the controller to implement ``pagelist`` and to create and
pass ``pages`` to our template:

.. parsed-literal::

    """Main Controller"""
    from wiki20.lib.base import BaseController
    from tg import expose, flash
    from pylons.i18n import ugettext as _
    import tg
    from tg import redirect, validate
    from wiki20.model import DBSession
    from wiki20.model.page import Page
    import re
    from docutils.core import publish_parts
    from sqlalchemy.exceptions import InvalidRequestError ######################

    wikiwords = re.compile(r"\b([A-Z]\w+[A-Z]+\w+)")

    class RootController(BaseController):

        @expose('wiki20.templates.page')
        def default(self, pagename="FrontPage"):
            try:
                page = DBSession.query(Page).filter_by(pagename=pagename).one()
            except InvalidRequestError:
                raise tg.redirect("notfound", pagename = pagename)
            content = publish_parts(page.data, writer_name="html")['fragment']
            root = tg.url('/')
            content = wikiwords.sub(r'<a href="%s\1">\1</a>' % root, content)
            return dict(content=content, page=page)

        @expose("wiki20.templates.edit")
        def notfound(self, pagename):
            page = Page(pagename=pagename, data="")
            DBSession.save(page)
            DBSession.commit()
            return dict(page=page)

        @expose(template="wiki20.templates.edit")
        def edit(self, pagename):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            return dict(page=page)

        @expose()
        def save(self, pagename, data, submit):
            page = DBSession.query(Page).filter_by(pagename=pagename).one()
            page.data = data
            DBSession.commit() # Tells database to commit changes permanently
            redirect("/"+pagename)

        **@expose("wiki20.templates.pagelist")**
        **def pagelist(self):**
            **pages = [page.pagename for page in DBSession.query(Page)]**
            **return dict(pages=pages)**

Here, we select all of the ``Page`` objects from the database, and order them by
pagename.

We can also modify ``page.html`` so that the link to the page list is available on
every page:

.. parsed-literal::

    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
      "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html
        xmlns="http://www.w3.org/1999/xhtml"
        xmlns:py="http://genshi.edgewall.org/"
        xmlns:xi="http://www.w3.org/2001/XInclude">

    <xi:include href="master.html" />

    <head>
        <meta content="text/html; charset=utf-8" http-equiv="Content-Type" py:replace="''"/>
        <title>${page.pagename} - 20-Minute Wiki</title>
    </head>

    <body>

    <div class="main_content">
    <div style="float:right; width: 10em;"> Viewing
    <span py:replace="page.pagename">Page Name Goes Here</span> <br/>
    Return to the <a href="/">FrontPage</a>.
    </div>
    <div py:replace="XML(content)">Formatted content goes here.</div>
    <a href="/edit/${page.pagename}">Edit this page</a><br/>
    **<a href="/pagelist">View the page list</a>**

    </div>

    </body></html>

You can see your pagelist by clicking the link on a page or by
going directly to http://localhost:8080/pagelist.


Further Exploration
============================================

Now that you have a working Wiki, there are a number of further places to explore:

#. You can add `JSON support via MochiKit <http://docs.turbogears.org/http%3A/docs.turbogears.org/2.0/Wiki20/JSONMochiKit>`_.

#. You can learn more about the `Genshi templating engine <http://genshi.edgewall.org/wiki/Documentation/templates.html>`_.

If you had any problems with this tutorial, or have ideas on how to make it
better, please let us know on the mailing list! Suggestions are almost always
incorporated.
