

Creating a password verification field
======================================

First lets take into consideration a very simple registration form::

 from tw.forms import TableForm, PasswordField, TextField
 from tw.api import WidgetsList

 class RegistrationForm(TableForm):
    action = 'register'
    class fields(WidgetsList):
        username = TextField()
        password = PasswordField()
        verify   = PasswordField()

Here is how the form is rendered:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/PasswordValidation?action=AttachFile&do=get&target=simple_register.png
    :alt: simple registration form

Now we will add a validator to the form before it is passed into the controller.  The validator code looks like this::

 from formencode import Schema
 from formencode.validators import FieldsMatch

 passwordValidator = Schema(chained_validators=(FieldsMatch('password',
                                                            'verify',
                                                             messages={'invalidNoMatch': 
                                                                  "Passwords do not match"}),))

We pass the new validator into the form when it is instantiated::

 registrationForm = RegistrationForm(validator=passwordValidator)

Finally, we pass the registration form to the controller in the normal way::


    @expose('genshi:mypackage.templates.register')
    def registration(self, **kw):
        pylons.c.form = registrationForm
        return dict(value=kw)

Notice that \*\*kw are sent into the controller method.  This is so that the user's results can be passed back to the form when the validation fails.

You need to display your widget in your template like this::

 ${tmpl_context.form(value=value)}

Finally, we direct the form to a "register" method so that you can add the user entry to the database, or do other things associated with registration::

    @validate(registrationForm, error_handler=registration)
    def registration(self, **kw):
        #this is where your user registration  would write to the database
        flash(_('your registration has succeeded, please wait for your administrator to activate your account'), status="ok")
        raise redirect('/')

Notice the validate decorator, which makes a call-back to the "registration" method.

When the validation fails, the result looks something like this:

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/PasswordValidation?action=AttachFile&do=get&target=passwordverify.png
    :alt: registration form with validation errors.
