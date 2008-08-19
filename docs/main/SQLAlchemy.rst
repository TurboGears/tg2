Working with SQLAlchemy and your data model
===========================================

`SQLAlchemy <http://www.sqlalchemy.org/>`_ is a modern `Object Relational Mapper <http://en.wikipedia.org/wiki/Object-relational_mapping>`_, that provides an extremely powerful and flexible system for managing the connection between in-memory Python objects and the relational datastore that provides persistence for those objects.  One of the main goals of SQLAlchemy is to allow for the full power of both Object Oriented development and Relational Algebra based datastores to be used together in a way that's natural to your application. 

TurboGears Integration
------------------------

TurboGears SQLAlchemy integration is entirely pushed into the generated quickstart template, so you are totally free to edit your model packages, remove all SQLAlchemy reference, and edit the same references out of environment.py. 

The main reason for this was not to make it easy to remove SQLAlchemy, it was to make it easier to build applications with multiple datastores, which is a common requirement for large-scale applications that either need to talk to so called `integration databases` which are shared between a large number of applications in an organization, or which need to do some horizontal partitioning of their database in order to scale up to thousands of requests per second. 

Getting Started
---------------------

If you don't know how SQLAlchemy works at all, please take a few minutes to read over these excellent tutorials:

* http://www.sqlalchemy.org/docs/05/ormtutorial.html -- which covers the ORM parts of SQLAlchemy
* http://www.sqlalchemy.org/docs/05/sqlexpression.html -- which covers using the SQLAlchemy expression language

Your quickstarted project will have a subpackage called `model`, made up of the following files:

* `__init__.py`: This is where the database access is setup. Your tables should be imported into this module, and you're highly encouaged to define them in a separate module - `entities`, for example.
* `identity.py`: This file will be created if you enabled identity in the quickstart. It defines the three tables TG2 identity relies on: `User` (for the registered members in your website), `Group` (for the teams a member may belong to, and to which you can assign permissions) and `Permission` (a permission granted to one or more groups); it also defines two intermediary tables: One for the many-to-many relationship between the groups and the permissions, and another one for the many-to-many relationship between the users and the groups.

Auto-reflection of tables has to happen after all the configuration is read, and the app is setup, so we provide simple init_model method (defined in `model/__init__.py`) that is not called until after everything is setup for you.


Defining your own tables
--------------------------

There are two methods for table definition with SQLAlchemy:

* The traditional, which consists in defining the table and a class to interact with this table, separately, and finally map the table to the relevant class. If you are new to SQLAlchemy, you're encouraged to start with the method below, because with this one things may seem more complicated.
* The declarative method, which relies on a built-in plugin for SQLAlchemy called `Declarative <http://www.sqlalchemy.org/docs/05/plugins.html#plugins_declarative>`_. This is the most intuitive method for table definition.

The tables defined by the quickstart in `model/identity.py` are based on the declarative method, so you may want to check it out to see how columns are defined for these tables, as well as to see real examples of many-to-one, one-to-many and many-to-many relationships. For more information, you may read `the ORM tutorial <http://www.sqlalchemy.org/docs/05/ormtutorial.html>`_ and the documentation for `the Declarative extension <http://www.sqlalchemy.org/docs/05/plugins.html#plugins_declarative>`_.

Once you have defined your tables in a separate module in the `model` package, they should be imported from `model/__init__.py`. So the end of this file would look like this:

.. code-block:: python

  # Import your model modules here. 
  from identity import User, Group, Permission
  # Say you defined these three classes in the 'movies'
  # module of your 'model' package.
  from movies import Movie, Actor, Director


Choosing data Types
---------------------

When you're setting up the column types for your tables, you don't have to think about your target database and it's type system.   SQLAlchemy provides a flexible underlying type system that, along with the table definition syntax above, allows you to database independent table objects. 

SQLAlchemy provides a number of built-in types which it automatically maps to underling database types.  If you want the latest and greatest listing just type:

.. code-block:: python

  >>> from sqlalchemy import types
  >>> dir(types)

Data Types
~~~~~~~~~~~

The main types are:

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

If you're following along with the tutorial, you'll want to make sure that you've defined the __init__ method.  We'll use the Movie class to create new Movie instances, and set their data all at once throughout the rest of the tutorial.

If you defined the __init__ method, it allows you to initialize the properties at the same time while you create the object::

  >>> entry = Movie(title='Dracula', year='1931', description='vampire movie')

or ::

  >>> entry = Movie('Dracula', '1931', 'vampire movie')

It looks better.


Using non-default names for identity-related tables and mapped classes
------------------------------------------------------------------------

If you don't want to use the default names for your identity-related tables and mapped classes, it's easy to replace them.

Once you have renamed the class names, go to `{your-app}/config/app_cfg.py` and edit these lines accordingly::

  # To replace the 'User' class by 'Member':
  base_config.sa_auth.user_class = model.Member
  # To use a different table name for the registered users:
  base_config.sa_auth.users_table = 'member'
  # To replace the 'Group' class by 'Team':
  base_config.sa_auth.group_class = model.Team
  # To use a different table name for the groups in your website:
  base_config.sa_auth.groups_table = 'team'
  # The Permission class and its table are not modified; we're happy with their names.
  base_config.sa_auth.permission_class = model.Permission
  base_config.sa_auth.permissions_table = 'permission'


Quick database creation
--------------------------

Once you've got your database table objects defined (and imported into __init__.py if you didn't define your model in __init__.py), you can create the tables in the database with one simple command, just run::

  paster setup-app development.ini

from within your project's home directory. 

Pylons (the TurboGears 2 underground framework) defines a setup-app function that paster will connect to the database and create all the tables we've defined. 

The default database setup configurations are defined in development.ini. So if you just run the script without modification of development.ini, the script will create a single-file database, which called 'devdata.db', in your project directory. If you change your data model and want to apply the new database, go delete 'devdata.db' and run the 'paster setup-app' command again.

TurboGears 2 does support database migrations. But that's another tutorial. 

Reference:

 * `SQLAlchemy Object Relational Tutorial <http://www.sqlalchemy.org/docs/05/ormtutorial.html>`_.
 * `Using Elixir with pylons <http://cleverdevil.org/computing/68/using-elixir-with-pylons>`_ (not supported yet).
 * `Elixir Tutorial <http://elixir.ematia.de/trac/wiki/TutorialDivingIn>`_ (not supported yet).


Getting help
-------------

If you need help with SQLAlchemy, you may:
 * Read the `SQLAlchemy documentation <http://www.sqlalchemy.org/docs/05/>`_.
 * Join the `SQLAlchemy mailing list <http://groups.google.com/group/sqlalchemy?hl=en>`_.
 * Join the `#sqlalchemy` channel on Freenode.


