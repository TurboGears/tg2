

Adding Captcha to your Form
===========================

What is tw.recaptcha?
-----------------------

tw.recaptcha is an extendtion to tw.forms TextField with a formencode validator. It keeps a form from being processed until there is proof that the form is being used by a human by forcing the human to analyze the image and type in the words that are shown.  It also has an audio clip you can listen to instead.

Why is tw.recaptcha good?
---------------------------
tw.recaptcha is good because like `ReCaptcha <http://recaptcha.net/>`_ the words you analyze are words that are scanned from old books that are being digitized.  The books are free and anyone can download and read them.  What happens is when the book is scanned it is broken up by word and those words are what is used in `ReCaptcha <http://recaptcha.net/>`_.  Since a scanner is not perfect and sometimes interprets the words incorrectly, the human answers the `ReCaptcha <http://recaptcha.net/>`_ sends back help to make the digital copies as accurate as possible and thus a pleasant experience for everyone. 


Installation
------------
::

 easy_install tw.recaptcha

If you have problems there is a way to manually get `ReCaptcha <http://recaptcha.net/>`_ working, often recaptcha-client does not install properly:

Download and install recaptcha-client on its own first.  If you want to try it all in one command using easy_install then you could try this (just doing _easy_install_ _recaptcha-client_ sometimes gives a broken egg)::

 easy_install recaptcha-client

If you get a broken egg download manually and install using the available setup.py::

 curl -O http://pypi.python.org/packages/source/r/recaptcha-client/recaptcha-client-1.0.1.tar.gz#md5=6a479f2142efc25954a6f37012b4c2dd
 tar -xvf recaptcha-client-1.0.1.tar.gz
 cd recaptcha-client-1.0.1
 python setup.py install

Now try easy_installing tw.recaptcha again

Usage
-------

First thing first.  Goto the `ReCaptcha <http://recaptcha.net/>`_ website and register your domain.  It is free.

Once that is done we can move onto the actual coding aspect.  

The first step is to make sure you have all of the imports that you need.  If you are already using forms and/or validation you may already have some of these::

 from tw.forms import TableForm
 from tw.recaptcha import ReCaptchaWidget
 from tw.recaptcha.validator import ReCaptchaValidator
 from tw.api import WidgetsList
 from formencode import Schema, NoDefault
 from formencode.validators import NotEmpty

Create a new Form to hold your recaptcha::

 class MyForm(TableForm):
    class fields(WidgetsList):
         recaptcha_response_field = ReCaptchaWidget(public_key='<your_public_key>')


Of course, we are going to need a validator, and since there are extra fields appended with the recaptcha widget, we are going to need a filtering schema to address the extra fields.  Alright, now with that done you need to setup your filtering schema class::

 class FilteringSchema(Schema):
    filter_extra_fields = False
    allow_extra_fields = True
    ignore_key_missing = False

Add the recaptcha validator to the list of chained validators for your form::

 validator = FilteringSchema(chained_validators=(ReCaptchaValidator(private_key='<your_private_key',  remote_ip='<your_domains_ip_address'),))

The next step is to create an instance of the form to pass into your page::

 captchaForm = MyForm(validator=validator)


That takes care of the creation process.  It should now load and work on your page.  Make sure the function that it goes to when you hit submit is expecting the two variables.  If you are using */*/kw then you are fine.  If you are specifying each one individually, then you will want to add the two variables into your def if you don't it will error saying it got values it wasn't expecting. Your code might look something like this::

 class MyController(BaseController):

    @expose("genshi:my.page.with.form.def")
    def showForm(self, **kw):
        pylons.c.form = captchaForm
        return dict(values=kw)

    @validate(captchaForm, error_handler=showForm)
    def storeFormData(self, myvar, myvar2, recaptcha_response_field=None, recaptcha_challenge_field=None):
        """My form storage code here"""
        return dict()

Once you are done you will end up with a captcha on your page that looks like

.. image:: http://docs.turbogears.org/2.0/RoughDocs/ToscaWidgets/Cookbook/ReCaptcha?action=AttachFile&do=get&target=recaptcha_field.jpg
