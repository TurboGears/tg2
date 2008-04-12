

Creating the data model
========================

:Status: Work in progress

.. contents:: Table of Contents
    :depth: 2

At the current stage, you could code your model with SQLAlchemy.

SQLAlchemy
----------

Edit model/__init__.py ::

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

And save it.

Types
--------

You could get all support types with following script::

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


ORM
---------

You could edit Movie object to support more object relational methods::

  class Movie(object):
      def __init__(self, title, year, description, **kw):
          self.title = title
          self.year = year
          self.description = description
    
      def __repr__(self):
          return "<Movie('%s','%s', '%s')>" % (self.title, self.year, self.description)


Please add the __init__ method section thus we'll use in the following tutorial.
The setting will lead you more easy to play with database.

For example, if you don't define the __init__ method. The general operating is::

  >>> entry = Movie()
  >>> entry.title = 'Dragula'
  >>> entry.year = '1931'
  >>> entry.description = 'vampire movie'

But if you defined the __init__ method, you could play with database in more pythonic way::

  >>> entry = Movie(title='Dragula', year='1931', description='vampire movie')

or ::

  >>> entry = Movie('Dragula', '1931', 'vampire movie')


Reference:

 * `SQLAlchemy Object Relational Tutorial <http://www.sqlalchemy.org/docs/04/ormtutorial.html>`_
 * `Using Elixir with pylons <http://cleverdevil.org/computing/68/using-elixir-with-pylons>`_ (not supported yet)
 * `Elixir Tutorial <http://elixir.ematia.de/trac/wiki/TutorialDivingIn>`_ (not supported yet)


