

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
  from moviecontroller import MovieController

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

* Use twForms with TurboGears 2
* http://wiki.pylonshq.com/display/toscawidgets/Using+twForms+with+Pylons.+Part+1
* all available forms::

  >>> from toscawidgets.widgets import forms
  >>> dir(forms)



