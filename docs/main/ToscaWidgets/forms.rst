Using ToscaWidgets to create Forms
==================================

Introduction
------------

One of the most useful features of ToscaWidgets is the ability to create forms with requisite validation.  Using existing form widgets it is relatively easy to add forms to your application to manage your database interactions.

The overall process for creating a form is as follows:

* create widgets for each field in the form.
* create a form widget passing in the field widgets as children.
* if you are creating an edit form, extract the row data from the database.
* call the widget in your template, passing in row data when appropriate.


Tutorial
-------------------

For this tutorial, we will be implementing a form to add a movie to a movie database.


Let's start with a simple SQLAlchemy model that has a Movie object like this ``model/__init__.py`` 

::

 # model/__init__.py
 movie_table = Table("movie", metadata,
     Column("id", types.Integer, primary_key=True),
     Column("title", types.String(100), nullable=False),
     Column("description", types.Text, nullable=True),
     Column("year", types.Integer, nullable=True),    
     Column("genre", types.String(100), nullable=True),
     Column("release_date", types.Date, nullable=True)    
     )
     
 class Movie(object):
     pass
     
 mapper(Movie, movie_table)

Our movie has a smattering of the different standard data types so that we can show off some simple ToscaWidgets form widgets.


Basic Form
----------

To create a form for the model add the following code in your root.py (this does not handle validation):

::

  from tw.forms import TableForm, TextField, CalendarDatePicker, SingleSelectField, TextArea
  from tw.api import WidgetsList

  class MovieForm(TableForm):
      # This WidgetsList is just a container
      class fields(WidgetsList):
          title = TextField()
          year = TextField(size=4)
          release_date = CalendarDatePicker()
          genrechoices = ((1,"Action & Adventure"),
                           (2,"Animation"),
                           (3,"Comedy"),
                           (4,"Documentary"),
                           (5,"Drama"),
                           (6,"Sci-Fi & Fantasy"))
          genre = SingleSelectField(options=genrechoices)
          description = TextArea()

  #then, we create an instance of this form
  create_movie_form = MovieForm("create_movie_form", action='create')

In ToscaWidgets, every widget can have child widgets. You can simply add nested classes which become children and then those child classes will be instantiated and appended to the widget.  In this case, we're adding some fields in a WidgetList to the FormTable.

Form Template
-------------
Create a new template in your templates directory, lets call it new_form.html.  Here is what the Genshi template should look like.

.. code-block:: html

 <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" 
       "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
 <html xmlns="http://www.w3.org/1999/xhtml"
       xmlns:py="http://genshi.edgewall.org/"
       xmlns:xi="http://www.w3.org/2001/XInclude">
 
 <!-- This line is important, since it will automatically handle including any required resources in the head -->
 <xi:include href="../master.html" />
 
 <head>
   <meta content="text/html; charset=UTF-8" http-equiv="content-type" py:replace="''"/>
   <title>Edit ${modelname}</title>
 </head>
 
 <body>
 <h1>New ${modelname}</h1>
 ${tmpl_context.form()}
 
 </body>
 </html>


The Controller
--------------

To show your form on the screen, we need to add a new controller method that looks like the following

::

     # we tell expose which template to use to display the form
     @expose("genshi:toscasample.templates.new_form")
     def new(self, **kw):
         """Form to add new record"""
         # Passing the form in the return dict is no longer kosher, you can 
         # set pylons.c.form instead and use c.form in your template
         # (remember to 'import pylons' too)
         pylons.c.form = model_form
         return dict(modelname='Movie')

Run the application, surf to `http://localhost:8080/new_form/ <http://localhost:8080/new_form/>`_ You will see a form that looks like this:


.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Forms?action=AttachFile&do=get&target=movie_form.png

Advanced Exercise
-----------------

Suppose we wanted to change the 'genre' options on the fly, for example look them up from a DB; you could return this info from the controller (not sure if this should be in form dict?):

::

        ...
        genreOptions = [(rec.id, rec.name) for rec in ImaginaryGeneraModel.query.all()]
        return dict(genreOptions=genreOptions, modelname='Movie')

Then in the template:

::

    ${tmpl_context.form(child_args={'genre': {'options': genreOptions}})}

This is left as an exercise for the reader.


Do More With Forms
------------------

Now, lets take a look at what we can do to customize the form to our liking.  

Field Attributes
~~~~~~~~~~~~~~~~

Each field has a set of attributes which we can change to suit our needs.  For example, perhaps you are not satisfied with the text area which is the default in twForms.  You can change the attributes of the text area simply by passing in a dictionary of attributes to the 'attr' parameter in the field definition.  The code to do this looks something like the following:

::

  description = TextArea(attrs={'rows':3, 'columns':25})

resulting in a field that looks like this:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Forms?action=AttachFile&do=get&target=text_area.png

Another problem with this form is that if you are using sqlite, the date is in the wrong format.  Lets give the CalendarDatePicker a date_format argument, and then our form will be viable.

::

  release_date = CalendarDatePicker(date_format='%y-%m-%d')

And now our date field has dashes in it instead of slashes:


.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Forms?action=AttachFile&do=get&target=date_picker.png


Fields and forms also have a set of shared arguments which you can use to change the display properties.  Here is a table of arguments and how they affect the widgets:

+-----------------+--------------------------------------------------------------------------------+
| *Name*          | *behavior*                                                                     |
+-----------------+--------------------------------------------------------------------------------+
| css_class       | change the class associated with the widget so you can customize look and feel.|
+-----------------+--------------------------------------------------------------------------------+
| *Field Specific parameters*                                                                      |
+-----------------+--------------------------------------------------------------------------------+
| disabled        | the field is shown but not editable                                            |
+-----------------+--------------------------------------------------------------------------------+
| show_error      | should the field show it's error (default is true)                             |
+-----------------+--------------------------------------------------------------------------------+
| label_text      | change the appearance of the text to the left of the field.                    |
+-----------------+--------------------------------------------------------------------------------+
| help_text       | change the tooltips text that appears when the user mouses over your field.    |
+-----------------+--------------------------------------------------------------------------------+
| *Form Specific parameters*                                                                       |
+-----------------+--------------------------------------------------------------------------------+
| submit_text     | change the words that appear on the submit button.                             |
+-----------------+--------------------------------------------------------------------------------+

Sometimes a developer desires to customize the form template to display the form in a certain manner (for instance, if you want two columns of entries)

Form Fields
~~~~~~~~~~~
Here is a quick and dirty list of all form fields that you can use:

TODO: each of these should link to an anchor in another page of form fields.

* BooleanRadioButtonList
* Button
* CalendarDatePicker
* CalendarDateTimePicker
* CheckBox
* CheckBoxList
* CheckBoxTable
* ContainerMixin
* FileField
* HiddenField
* ImageButton
* MultipleSelectField
* PasswordField
* RadioButton
* RadioButtonList
* ResetButton
* SecureTicketField
* SelectionField
* SelectionList
* SingleSelectField
* SingleSelectionMixin
* SubmitButton
* TextArea
* TextField

Form Validation
--------------------
Form validation is a very powerful way to make sure that the data which your user's enter is formatted in a predictable manner long before database interaction happens.  When data entered in to a form does not match that which is required, the user should be redirected back to the form to re-enter their data.  A message indicating the problem should be displayed for all fields which are in error at the same time.  ToscaWidgets take advantage of the work done in FormEncode to do it's validation.  See the docs at  `FormEncode <http://www.formencode.org/>`_ for more information. 

The first thing we need to do is add a validator to each of the fields which we would like validated.  Each InputWidget takes a validator argument.  The form itself is then passed into a method decorator which checks to see if the data coming in from the client matches validates against the validator defined in the widget.  Our new form looks something like this:

::

  from formencode.validators import Int, NotEmpty, DateConverter, DateValidator


  class MovieForm(TableForm):
      # This WidgetsList is just a container
      class fields(WidgetsList):
          title = TextField(validator=NotEmpty)
          year = TextField(size=4, validator=Int(min=1900, max=2100))
          release_date = CalendarDatePicker(validator=DateConverter())
          genrechoices = ((1,"Action & Adventure"),
                           (2,"Animation"),
                           (3,"Comedy"),
                           (4,"Documentary"),
                           (5,"Drama"),
                           (6,"Sci-Fi & Fantasy"))
          genre = SingleSelectField(options=genrechoices)
          description = TextArea(attrs=dict(rows=3, cols=25))

Note that we removed the date format from the CalendarDatePicker.  This is because the DateConverter will take whatever date is entered in the box and convert it to a datetime object, which is much better understood by the orm than a date string.

Our controller gets a new validator decorator for the creation of the movie entry.

::

    @validate(new_movie, error_handler=new)
    @expose()
    def create(self, **kw):
        """A movie and save it to the database"""
        movie = Movie()
        movie.title = kw['title']
        movie.year = kw['year']
        movie.release_date = kw['release_date']
        movie.descrpition = kw['description']
        movie.genre = kw['genre']
        DBSession.save(movie)
        DBSession.commit()
        flash("Movie was successfully created.")
        raise redirect("list")



And the resulting form on a bad entry will give you a output like this:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Forms?action=AttachFile&do=get&target=validators.png


In short, there are many things you can do with validators, but that the above example gives you a basic understanding of how validators can be used to check user input.

Available Validators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Attribute
* Bool
* CIDR
* ConfirmType
* Constant
* CreditCardExpires
* CreditCardSecurityCode
* CreditCardValidator
* DateConverter
* DateTime
* DateValidator
* DictConverter
* Email
* Empty
* False
* FancyValidator
* FieldStorageUploadConverter
* FieldsMatch
* FileUploadKeeper
* FormValidator
* IDeclarative
* IPhoneNumberValidator
* ISchema
* IValidator
* Identity
* IndexListConverter
* Int
* Interface
* Invalid
* MACAddress
* MaxLength
* MinLength
* NoDefault
* NotEmpty
* Number
* OneOf
* PhoneNumber
* PlainText
* PostalCode
* Regex
* RequireIfMissing
* RequireIfPresent
* Set
* SignedString
* StateProvince
* String
* StringBool
* StringBoolean
* StripField
* TimeConverter
* True
* URL
* UnicodeString
* Validator
* Wrapper
