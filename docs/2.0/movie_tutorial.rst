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

Your first step when using SQLAlchemy in TurboGears is to edit your model/__init__.py :

.. code-block: python 

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

Types
--------

SQLAlchemy provides a number of built-in types which it automatically maps to underling database types.  If you want the latest and greatest listing just type:

.. code-block: python

  >>> from sqlalchemy import types
  >>> dir(types)

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
-----------

============  ==========
 property     value      
============  ==========
 primary_key  True/False 
 nullable     True/False 
============  ==========


Object Relational Mapping
-----------------------------

Once you've got a table, such as the movie_table we're using in this example you can create a Movie class to support a more object oriented way of looking at your data::

  class Movie(object):
      def __init__(self, title, year, description, **kw):
          self.title = title
          self.year = year
          self.description = description
    
      def __repr__(self):
          return "<Movie('%s','%s', '%s')>" % (self.title, self.year, self.description)


If you're following along with the tuturial, you'll want to make sure you custom __init__ method.  We'll use this to creae new Movie instances, and set their data all at once througout the rest of the tutorial. 


If you don't define the __init__ method. You will need to update the properties of a movie object after it's been created like this::

  >>> entry = Movie()
  >>> entry.title = 'Dragula'
  >>> entry.year = '1931'
  >>> entry.description = 'vampire movie'

But if the __init__ method we defined allows you to initialize the properties at the same time you create the object::

  >>> entry = Movie(title='Drakula', year='1931', description='vampire movie')

or ::

  >>> entry = Movie('Drakula', '1931', 'vampire movie')

  #format rst

  Bootstrapping the application with CRUD
  ========================================

  :Status: Work in progres

  .. contents:: Table of Contents
      :depth: 2

  There are 2 options for building the controllers to use your model, build it yourself using the ORM, or generate a basic interface automatically using CRUD.


  Use ORM
  ---------

  Edit controllers/root.py::

    from my-project-name.lib.base import BaseController
    from tg import expose, flash
    from my-project-name.model import DBSession, Movie

    class RootController(BaseController):

        ....

        @expose('my-project-name.templates.index')
        def show(self):
            flash("create model")

            # create entry
            entry = Movie("Transformer", 2007, "Cars and robots")          
            # create entry if not define model object __init__ method
            #entry = Movie()
            #entry.title="Transformer"
            #entry.year=2007
            #entry.description ="Cars and robots"


            # save entry
            DBSession.save(entry)
            DBSession.commit()

            # query record from Movie object
            record = DBSession.query(Movie).filter(Movie.title=='Transformer').one()

            return dict(record=record.title)


  Edit template/index.html and add::

      <h1 py:replace="record">record</h1>


  Use CRUD tool
  --------------

  You could use paster command to create a customizable interface to Create, Read, Update, Delete records 
  (CRUD) based on model ::

    $ paster crud
    Note: Make sure you have created your models first
    Enter the model name: Movie
    Enter the primary key [id]: 
    Enter the package name [MovieController]:
    Enter the model form name [MovieForm]: 

  or use short command without prompt::

    $ paster crud -i id Movie MovieController

  The command Create several files

   * controllers/MovieController.py
   * controllers/MovieForm.py
   * templates/MovieController/list.html
   * templates/MovieController/show.html
   * templates/MovieController/form.html

  Edit controllers/root.py::

    ....
    from MovieController import MovieController

    class RootController(BaseController):
        movie = MovieController()

        @expose('www.templates.index')
        def index(self):
            from datetime import datetime
            flash("Your application is now running")
            return dict(now=datetime.now())

  Browse http://localhost:8080/movie/ and you got an Movie model admin interface. Note that the trailing '/' is important here.

  Edit MovieForm.py to customize the field corresponding to your model. 

  And edit list.html/show.html to decide which column you want to show.


  Reference
  ----------

 * `SQLAlchemy Object Relational Tutorial <http://www.sqlalchemy.org/docs/04/ormtutorial.html>`_
 * `Using Elixir with pylons <http://cleverdevil.org/computing/68/using-elixir-with-pylons>`_ (not supported yet)
 * `Elixir Tutorial <http://elixir.ematia.de/trac/wiki/TutorialDivingIn>`_ (not supported yet)
