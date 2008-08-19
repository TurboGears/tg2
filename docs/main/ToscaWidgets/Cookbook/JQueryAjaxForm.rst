
JQuery AjaxForm Widget
==========================


Installation
------------

::
  
  easy_install tw.jquery


Usage
-----

The AjaxForm widget supports the following parameters:

Mandatory Parameters:
~~~~~~~~~~~~~~~~~~~~~
* **id** The id of the form. The submit action of this form triggers the Ajax Request. 

* **fields** The form fields. The fields could be a WidgetList object created like this::

    from formencode import validators
    from tw.forms.fields import TextField, TextArea, CheckBox
    from tw.api import WidgetsList

    class CommentFields(WidgetsList):
        """The WidgetsList defines the fields of the form."""

        name = TextField(validator=validators.NotEmpty())
        email = TextField(validator=validators.Email(not_empty=True),
                        attrs={'size':30})
        comment = TextArea(validator=validators.NotEmpty())
        notify = CheckBox(label="Notify me")
* **action** The url for the controller method that would handle the Ajax Request.

Optional Parameters:
~~~~~~~~~~~~~~~~~~~~
* **target** This is the id of the element where the output of the request would be rendered. (*Default:* "output")

* **type** The method to use for the request, i.e. whether GET or POST. (*Default:* "POST")

* **dataType** The dataType of the response, i.e. whether XML, JSON or SCRIPT. (*Default:* "JSON")

* **beforeSubmit** The javascript function that should be called just before submitting the request. This could be helpful 

for doing javascript based validations if needed. (*Default:* None)

* **success** The javascript function that should be called if the request succeeds. (*Default:* None)

* **clearForm** Clears the form after sending the request. (*Default:* True)

* **resetForm** Resets the form after sending the request. (*Default:* True)

* **timeout** Time in ms before the request is timed out. (*Default:* 3000)

A simple AjaxForm widget may be instantiated as::

    from tw.jquery import ActiveForm

    ajax_form = ActiveForm(id="myAjaxForm",
                        fields=CommentFields(),
                        target="output",
                        action="do_search")


The form can then be served up to the user via a controller method like this::
  
   @expose('mypackage.templates.myformtemplate')
   def entry(self, **kw):
       pylons.c.form = myAjaxForm
       return dict(value=kw)

And your template form would display your form like this::

   ${tmpl_context.form(show_labels=True, value=value)}

And here is the resulting field when viewed from a browser:

.. image:: 
       http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/JQueryAjaxForm?action=AttachFile&do=get&target=ajaxform1.png
    :alt: example AjaxForm


The template generates the necessary javascript code to send the Ajax Request when the form is submitted. The controller code 

for generating the response would be something like::

    @expose()
    @validate(ajax_form, error_handler=entry)
    def do_search(self, **kw):
        return "<p>Recieved Data:<br/>%(name)s<br/>%(email)s<br/>%(comment)s<br/>%(notify)s<br/></p>" % kw

The output would be rendered inside a div element called *output*, which is the default target element. This is how the page 

looks like after the form has been successfully submitted:

.. image:: 
       http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/JQueryAjaxForm?action=AttachFile&do=get&target=ajaxform2.png
    :alt: example AjaxForm


--To DO : Getting output as JSON and updating a data grid ---

