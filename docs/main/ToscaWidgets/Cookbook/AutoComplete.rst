

JQuery AutoComplete Widget
==========================


Installation
------------

::
  
  easy_install tw.jquery


Usage
-----

The AutoCompleteField widget supports the following parameters:

Mandatory Parameters:
~~~~~~~~~~~~~~~~~~~~~
* **id** The element id of the input field element. Multiple instanes of AutoCompleteField can be used on the same form or page. These are referenced distinctly on the form or page by the id.  This is also the name of the field which is passed into the form on the server side.
* **completionURL** This is the url to be used for fetching the autocomplete values using HTTP GET request.

Optional Parameters:
~~~~~~~~~~~~~~~~~~~~
* **fetchJSON** Specifies whether the values are to be fetched as a JSON request. If specified as true it tries to interpret the returned data as JSON. (*Default:* fetchJSON = False)
*  **minChars** Specifies the minimum number of characters that the user must enter before the list is shown. (*Default:* minChars = 1)

For example the widget is instantiated as::

    from tw.jquery.autocomplete import AutoCompleteField

    autoField = AutoCompleteField(
                       id='myFieldName',
                       completionURL = 'fetch_states',
                       fetchJSON = True,
                       minChars = 1)


Once the Widget is instantiated it can be added to an existing form::

   from tw.forms import TableForm

   myForm = TableForm(id='myForm', children=[autoField])

This form is of course served up to the user via a controller method like this::
  
   @expose('mypackage.templates.myformtemplate')
   def entry(self, **kw):
       pylons.c.form = myForm
       return dict(value=kw)

And your template form would display your form like this::

   ${tmpl_context.form(value=value)}

And here is the resulting field when viewed from a browser:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook?action=AttachFile&do=get&target=autocomplete1.png
    :alt: example AutoComplete Field


The template generates the necessary javascript code to fetch values from the controller using the completionURL. The controller code for generating the json response would be something like::

    @expose('json')
    def fetch_states(self):
        states = ['ALASKA', 'ALABAMA', 'ARIZONA', ..........., 'WYOMING']
        return dict(data=states)

The method should return a dictionary with **data** as key and a list as value. In this example the list is populated manually. The list would, in most cases, be obtained from a database.


Data Retrieval
--------------

Here is how you retrieve data from the form once it has been submitted by the user.  Notice that this is not any different from how it is normally retrieved from forms.::

  def retrieve(self, **kw):
     do.something()
     return dict()


Validation
----------
We add a @validate decorator to the data retrieval function which redirects us back to the original form if the user enters something that does not match that which is in our list. ::

  @validate(myForm, error_handler=entry)
  def retrieve(self, **kw):
     do.something()
     return dict()

and here is what the widget looks like when the validation fails:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/AutoComplete?action=AttachFile&do=get&target=autocomplete3.png
    :alt: example Validation Failure



--what about if someone is using this widget for a select field, and the value they want returned is the value of the id of an object of select values in a database? ---
