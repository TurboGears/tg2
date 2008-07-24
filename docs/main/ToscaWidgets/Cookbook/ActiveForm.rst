

Creating Ajax-enabled forms using Prototype
===========================================

Installation
------------

::

 easy_install tw.prototype

Usage
-----

::

 from tg import expose, flash, redirect, TGController
 import pylons

 from tw.forms.fields import *
 from tw.prototype.activeform import ActiveForm
 from twtools.frameworks.tg2.activeform import ActiveFormResponseHandler

 from formencode.validators import Int, String

 children = [TextField('non_empty_string', validator=String(not_empty=True)),
            TextField('integer', validator=Int()),
            ]
 activeForm = ActiveForm(id='myActiveForm', 
                         action='submit', 
                         children=children, 
                         clear_on_success=True,
                         on_success="console.log('hello!')")

 class ExampleController(TGController):

    @expose('tw.prototype.examples.tg2.templates.index')
    def form(self, **kw):
        pylons.c.widget = activeForm
        return dict()

    def submitSuccess(self, **kw):
        #this is where your database call goes
        print kw

    activeFormHandler = ActiveFormResponseHandler(activeForm, submitSuccess)
    submit            = activeFormHandler.ajax_submit
