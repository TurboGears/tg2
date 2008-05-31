Working with SQLAlchemy and your data model
===========================================

SQLAlchemy is a modern Object Relational Database, that provides and extremely powerful and flexible system for managing the connection between in-menory python objects and the relational datastore that provides persistence for those objects.  One of the main goals of SQLAlchemy is to allow for the full power of both Object Oriented development and Relational Algebra based datastores to be used together in a way that's natural to your application. 

TurboGears Integration
------------------------

TurboGears SQLAlchemy integration is entirely pushed into the generated quickstart template, so you are totally free to edit the __init__.py file in your model directory, remove all SQLAlchemy reference, and edit the same references out of environment.cfg. 

The main reason for this was not to make it easy to remove SQLAlchemy, it was to make it easier to build applications with multiple datastores, which is a common requirement for large-scale applications that either need to talk to so called `integration databases` which are shared between a large number of applications in an organization, or which need to do some horizontal partitioning of their database in order to scale up to thousands of requests per second. 

Getting Started
---------------------

If you don't know how SQLAlchemy works at all, please take a few minutes to read over these excellent tutorials:

* http://www.sqlalchemy.org/docs/04/ormtutorial.html -- which covers the ORM parts of SQLAlchemy
* http://www.sqlalchemy.org/docs/04/sqlexpression.html -- which covers using the SQLAlchemy expression language

Your first step when using SQLAlchemy in TurboGears is to edit your model/__init__.py:

.. code-block:: python

      from pylons import config
      from sqlalchemy import Column, MetaData, Table, types
      from sqlalchemy.orm import mapper, relation
      from sqlalchemy.orm import scoped_session, sessionmaker
      
      # Global session manager.  Session() returns the session object
      # appropriate for the current web request.
      DBSession = scoped_session(sessionmaker(autoflush=True, transactional=True))
      
      # Global metadata. If you have multiple databases with overlapping table
      # names, you'll need a metadata for each database.
      metadata = MetaData()
      
      def init_model(engine):
          """Call me before using any of the tables or classes in the model."""
          # Reflected tables must be defined and mapped here.
          
      # Normal tables may be defined and mapped at module level, or here:
      
      # Create a table
      movie_table = Table("movie", metadata,
          Column("id", types.Integer, primary_key=True),
          Column("title", types.String(100), nullable=False),
          Column("year", types.Integer, nullable=False),
          Column("description", types.String(256), nullable=True),
          )
          
          
      # Define ORM classes (often called "mapped classes").
      # attributes will be added by the mapper below
      class Movie(object):
          pass
          
      # Map each class to its corresponding table.
      mapper(Movie, movie_table)

Auto-reflection of tables has to happen after all the configuration is read, and the app is setup, so we provide simple init_model method that is not called until after everything is setup for you.  

But if you're createing a new app, and want to define your tables in python, feel free to just create something like the movie_table we show in the code snipit above. 

Choosing data Types
---------------------

When you're setting up the column typess for your tables, you don't have to think about your target database and it's type system.   SQLAlchemy provides a flexible underying type system that, along with the table definition syntax above, allows you to database independent table objects. 

SQLAlchemy provides a number of built-in types which it automatically maps to underling database types.  If you want the latest and greatest listing just type:

.. code-block:: python

  >>> from sqlalchemy import types
  >>> dir(types)

Data Types
~~~~~~~~~~~

main types are:

================ ========
 type            value    
================ ========
 types.Binary    binary   
 types.Boolean   boolean  
 types.Integer   integer  
 types.Numeric   number   
 types.String    string   
 types.Date      date     
 types.Time      time     
 types.DateTime  datetime 
================ ========


Properties
~~~~~~~~~~~

While you define the Columns, you could specify several properties to control the column's behaviors.

============  ==========
 property     value      
============  ==========
 primary_key  True/False 
 nullable     True/False 
============  ==========


Basic Object Relational Mapping
---------------------------------

Once you've got a table, such as the movie_table we're using in this example, you can create a Movie class to support a more object oriented way of manipulating your data::

  class Movie(object):
      def __init__(self, title, year, description, **kw):
          self.title = title
          self.year = year
          self.description = description

      def __repr__(self):
          return "<Movie('%s','%s', '%s')>" % (self.title, self.year, self.description)


If you don't define the __init__ method. You will need to update the properties of a movie object after it's been created. like this::

  >>> entry = Movie()
  >>> entry.title = 'Dragula'
  >>> entry.year = '1931'
  >>> entry.description = 'vampire movie'

If you're following along with the tuturial, you'll want to make sure that you've defined the __init__ method.  We'll use the Movie class to creae new Movie instances, and set their data all at once througout the rest of the tutorial.

If you defined the __init__ method, it allows you to initialize the properties at the same time while you create the object::

  >>> entry = Movie(title='Dracula', year='1931', description='vampire movie')

or ::

  >>> entry = Movie('Dracula', '1931', 'vampire movie')

It looks better.


Quick database creation
--------------------------

Once you've got your database table objects defined (and imported into __init__.py if you didn't define your model in __init__.py), you can create the tables in the database with one simple command, just run::

  paster setup-app development.ini

from within your project's home directory. 

Pylons (The TurboGears 2 underground framework) defines a setup-app function that paster will connect to the database and create all the tables we've defined. 

The default database setup configurations are defined in development.ini. So if you just run the script without modification of development.ini, the script will create a single-file database, which called 'devdata.db', in your project directory. If you change your data model and want to apply the new database, go delete 'devdata.db' and run the 'paster setup-app' command again.

TurboGears 2 does support database migrations. But that's another tutorial. 

Reference:

 * `SQLAlchemy Object Relational Tutorial <http://www.sqlalchemy.org/docs/04/ormtutorial.html>`_
 * `Using Elixir with pylons <http://cleverdevil.org/computing/68/using-elixir-with-pylons>`_ (not supported yet)
 * `Elixir Tutorial <http://elixir.ematia.de/trac/wiki/TutorialDivingIn>`_ (not supported yet)


