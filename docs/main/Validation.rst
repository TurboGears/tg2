FormEncode @validate, and TurboGears Validation
==================================================

When using TurboGears, your controller methods get their arguments built from
the various GET, POST, and URL mechanisms provided by TurboGears. The only
downside is that all the arguments will be strings and you'd like them
converted to their normal Python datatype: numbers to ``int``, dates to
``datetime``, etc.

This conversion functionality is provided by the `FormEncode`_ package and is
applied to your methods using the ``@validate()`` decorator. FormEncode
provides both validation and conversion as a single step, reasoning that you
frequently need to validate something before you can convert it or that you'll
need to convert something before you can really validate it.

The ``@validate()`` decorator can evaluate both widget-based forms and the
standard form arguments so they are not dependent on widgets at all. 

Furthermore, the ``@validate()`` decorator is not really required at all. 
It just provides a convenience so that you can assume that you have the right
kind of data inside your controller methods. This helps separate validation logic
from application logic about what to do with valid data.  

If you don't put a ``@validate()`` decorator on your method, you'll simply 
have to do the string conversion in your controller. 


Validating arguments (without form widgets)
-------------------------------------------

When not using forms, the story gets a bit more complex. Basically, you need to
specify which validator goes with which argument using the ``validators``
keyword argument. Here's a simple example::
    
    @expose('json')
    @validate(validators={"a":validators.Int(), "b":validators.Email})
    def two_validators(self, a=None, b=None, *args):
        errors = [{key, value} in pylons.c.form_errors.itteritems()]
        values =  pylons.c.form_values
        return dict(a=a, b=b, errors=str(errors), values=str(values))

The dictionary passed to validators maps the incoming field names to the
appropriate FormEncode validators, ``Int`` in this example. 

If there's a validation error, TurboGears calls the error_handler if it exists, 
but it always adds form_errors and form_values to the tmpl_context, so they will 
be available there for the rest of the request.   In this case if there are validation
errors, we grab both the error messages and the original `unvalidated` values 
and return them in the error message. 

FormEncode and TurboGears provide a number of useful pre-made validators
for you to use,  are available in the ``turbogears.validators`` module.

For most validators, you can pass keyword arguments for more specific
constraints. 

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

For the absolute most up-to date list of available validators, check the `FormEncode
validators`_  module. You can also create your own validators or build on 
existing validators by inheriting from one of the defaults. 

See the FormEncode documentation for how this is done.

.. _`FormEncode validators`: http://formencode.org/module-formencode.validators.html#classes
.. _TurboGears validators: http://tg.maetico.com/api/public/turbogears.validators-module.html
.. _source: http://trac.turbogears.org/browser/branches/1.0/turbogears/validators.py


Validating widget based forms
-------------------------------

The simplest way to use ``@validate()`` is to pass in a reference to a
widgets-based form::

    @validate(projectname.forms.a_form)

The widgets system will take care of building a schema to handle the data
conversions and you'll wind up with the ``int`` or ``datetime`` objects you
specified when building the form. When paired with the `validate`
decorator, you can handle the common case of building a form, validating it,
redisplaying the form if there are errors, and converting a valid form into the proper arguments in only a few lines of Python.

You can also pass the form using a keyword augment:

.. code-block:: python

    @validate(form=projectname.forms.a_form)
    
You might also want to tell TurboGears to pass of handling of invalid data
to a different controller, to do that you just pass the method you want called
to @validate via the error_handler param::

    @validate(forms.myform, error_handler=process_form_errors)

The method in question will be called, with the unvalidated data as it's params. 
And error validation messages will be stored in pylons.tmpl_context.

Here's a quick example of how this all works:

.. code-block:: python

    @expose('json')
    @validate(form=myform)
    def process_form_errors(self, **kwargs):
        #add error messages to the kwargs dictionary and return it
        kwargs['errors'] = pylons.tmpl_context.form_errors
        return dict(kwargs)
    
    @expose('json')
    @validate(form=myform, error_handler=process_form_errors)
    def send_to_error_handler(self, **kwargs):
        return dict(kwargs)

If there's a validation error in myform, the send_to_error_handler method will never get called.  Instead process_form_errors will get called, and the validation error messages can be picked up from the form_errors value of the template context object (pylons.tmpl_context).

Schema validation
----------------------

Sometimes you need more power and flexibility than you can get from validating
individual form fields.   Fortuanately FormEncode provides just the thing for
us -- Schema validators. 

If you want to do multiple-field validation, reuse validators or just clean up
your code, validation ``Schema``'s are the way to go. You create a validation
schema by inheriting from ``turbogears.validators.Schema`` and pass the newly
created ``Schema`` as the ``validators`` argument instead of passing a
dictionary.  

Create a schema::

    class PwdSchema(validators.Schema):
        pwd1 = validators.String(not_empty=True)
        pwd2 = validators.String(not_empty=True)
        chained_validators = [validators.FieldsMatch('pwd1', 'pwd2')]

Then you can use that schema in @validate rather than a dictionary of validators::

    @expose()    
    @validate(validators=PwdSchema())
    def password(self, pwd1, pwd2):
        if pylons.c.form_errors:
            return "There was an error"
        else:
            return "Password ok!"

Besides noticing our brilliant security strategy, please notice the
``chained_validators`` part of the schema that guarantees a pair of matching
fields.

Again, for information about ``Invalid`` exception objects, creating your own
validators, schema and FormEncode in general, a refer to the `FormEncode
Validator`_ documentation and don't be afraid to check the
``Formencode.validators`` source. It's often more clear than the docs.

.. _`FormEncode Validator`: http://formencode.org/docs/Validator.html

Converting URL strings to Python types manually
-----------------------------------------------

You can always use e.g. Python's ``int()`` method to convert
a string to an integer and use a try/except block to catch
errors in the conversion process::

  from turbogears import controllers, expose
  class Root(controllers.RootController):

  #...
      # return the result of x+y
      @expose()
      def addnum(self, x, y)
          try:
             return str(int(x)+int(y))
          except:
             return 'value is not valid'
    
This isn't that hard, but it quickly becomes unwieldy when you
start converting large numbers of arguments. Moreover, you
still have the problem of propagating the errors back to your
users. In the end, it's usually far simpler to use the
validation framework.

.. _FormEncode: http://formencode.org/