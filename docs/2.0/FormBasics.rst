TurboGears Form handling overview:
===================================

The first thing to say about TurboGears form handling is that we turn form
submision values in to Controller params, and allow you to do whatever you 
want for form generation/submission in the templates. 

So, you can always handle forms without using any of these tools, forms can be 
coded up in your templates, and the values can be processed in your controlle. 

But creating forms, processing form results, and handling form errors is one of 
the most common activites TG2 provides several tools to help you make forms 
with complex javascript enabled features quickly and easily, and to make 
handling validation errors, and requesting updated information from your users 
easy. 

Overview of the tools
-----------------------------------

There are three basic things that can be done to help manage forms.  

#. Make it easy to create a new form, perhaps with fancy calendar fields, etc. 
#. Make it easy to validate form contents, and transform form results into 
   Python objects. 
#. Make it easy to re-display form results with associated error messages. 

Rather than re-invent the wheel for these three things TurboGears has brought 
together and integrated a couple of projects that do these things. 

Validation is handled by FormEncode, form generation by ToscaWidgets, and model
introspection+automatic form and validator generation can be provided by DBSprockets.

We've integrated these things together so you automatically generate forms
with appropriate validators, and automatically handle form errors in a simple 
way.

You can make a new form from a database table (using DBSprockets) like this::

    from dbsprockets.primitives import makeForm
    from myProject.myModel import User
    
    login_form = makeForm(User, identifier='myLoginForm', action='/login', limitFields=['user_name', 'password'])
    
This form is actually a ToscaWidgets CompoundWidget object, with member widgets for each of the form fields, and with some code to wrap them up in a form and display them to the user.  DBSprockets takes the User object introspects it's table information, and makes a form for you.   In this case, we're limiting the fields that show up on the form to those needed for the user_name and password columns.   

We can then add that widget to the list of widgets available in the template by adding it to tmpl_context.widgets in your controller::

  TODO: Add example code here

And then you can display it in your template by calling it like this:::

  TODO: add code here

When you get the results back in your login method you can automatically validate the form using::

  @validate(form=login_form)
  def login(user_name, password):
      return dict()

And if there are errors, they will be saved in ``tmpl_context.form_errors`` which is automatically availabel in your template.   And the widget is designed to look trough tmpl_context.form_errors for error messages and display them along side the form when it's displayed.  That way you can use the same template, and the same widget to redisplay the form along with the errors whenever there are form validation errors.
 
