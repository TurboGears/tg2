Simple Widget Form Tutorial
===========================

:Status: RoughDoc

.. contents:: Table of Contents
   :depth: 2


This tutorial introduces you to the widget form system by building a simple
application that accepts and displays comments.

The comments are listed on the index page and a link at the bottom of the page
directs the user to add a comment. To keep things simple, we're going to skip
the database and just keep track of our comments in memory using a global
``comments`` variable.

The comments form itself requires both a name, an email address and a comment
to be entered. If input to one of the fields is missing, the form is
redisplayed along with a message next to the appropriate field. We've tossed
in a checkbox field to give an example that widgets also handle values of other
type than strings, i.e. booleans, integers etc.

Successfully completing a form adds the comment to the global comments
variable and displays a success message on the index page.


Starting the Project
--------------------

This tutorial starts with a `pre-built project`_. Please download and unpack
the provided archive with the complete example project and read the source
code along with the tutorial.  For a detailed explanation on how to create a
new project, please read `20 Minute Wiki Tutorial`_.

.. _pre-built project: attachment:FormsTutorial-2.0.tgz
.. _20 Minute Wiki tutorial: main/Wiki20/All

If you're not already familiar with the basics of what widgets are, and how they work, you'll probably wan to take a look at `the widgets overview page <WidgetsOverview>`_

Intro to Widgets and Forms
--------------------------
The single most common use of Widgets in a TurboGears project is in building forms.

Widgets make form creation really easy, because they address all the important
aspects of form handling:

  * Defining which fields the form has
  * Injecting Javascript and CSS for a field if necessary
  * Defining which kind of input each field expects
  * Wrapping the fields into a form
  * Displaying the form
  * Validating form input
  * Displaying validation errors and re-displaying user input

For the purpose of this tutorial, we are interested in two main types of
widgets: *simple* form field widgets -- text inputs and checkboxes -- and
*compound* widgets like the form itself.

Simple form field widgets generally correspond to the default browser inputs
but some, like the date picker, have extra smarts to make your user's lives
easier. You can get an overview of which widgets are available on your install
by checking out the `widget browser`_ in the `toolbox`_.

(Note that the toolbox and widget browser are not yet implemented in TG 2.0.  The 1.0 versions are substantially accurate for 2.0, however.)

.. _widget browser: 1.0/WidgetBrowser
.. _toolbox: 1.0/Toolbox

Compound widgets, like forms, usually act as containers for fields. In
particular, a forms provides layout (Table or List) for its fields and is
responsible for labels and error display.

There are many other types of standard widgets, and you can create your own
custom widgets, but this is a simple widgets tutorial, so we're keeping it
simple. For more information about the widgets framework, you can start
reading at the general `widgets overview`_.

.. _widgets overview: main/WidgetsOverview

Defining the form
-----------------

With the introduction out of the way, let's dive into the code. This is the
form field declaration in ``formstutorialtg2/controllers/root.py``::

    class CommentFields(WidgetsList):
        """The WidgetsList defines the fields of the form."""

        name = forms.TextField(validator=validators.NotEmpty())
        email = fomss.TextField(validator=validators.Email(not_empty=True),
          attrs={'size':30})
        comment = forms.TextArea(validator=validators.NotEmpty())
        notify = forms.CheckBox(label="Notify me")

As you can see, the declaration looks quite a bit like a SQLAlchemy class
definition. The ``CommentFields`` class declares a list of four widgets, all
of which are simple widgets corresponding to the similarly named ``<INPUT>``
tags in HTML. The first three are required text fields and the ``email`` field
requires a well-formed email address.

Notice that we have not defined a field widget for the submit button. The
``TableForm`` and ``ListForm`` widgets take care of this for you by default
and you can tweak it using their ``submit_text`` argument.

Now the above snippet won't get you a form as is, it's just a list of widgets.
To build a form, you pass the list of widgets into a form constructor (both
``TableForm`` and ``ListForm`` are standard widgets) and get a compound
form widget::

    comment_form = forms.TableForm(
        fields=CommentFields(),
        action="save"
    )

Maybe you can guess what the extra ``action`` argument is for: it defines the
``action`` attribute of the form element in the generated HTML, which means
that submissions from the form will go to ``http://mysite/save`` and will be
handled by the ``save`` method of our controller.

.. tip:: If, for some reason, you do want to manage the submit button
         yourself, derive your own widget form class from ``TableForm`` or
         ``ListForm`` and overwrite the ``submit`` attribute with your own
         instance of a ``forms.SubmitButton``.

Displaying the comment form
---------------------------

Working our way down ``root.py``, our first stop is the ``add`` method.
This method passes the widget form instance ``comment_form``, which we just
covered, to the template ``add.html``::

    @expose(template='formstutorialtg2.templates.add')
    def add(self):
        """Show the comment form."""

        if pylons.c.form_errors:
            flash('There was a problem with the form!')
        return dict(form=comment_form)

We'll talk about ``form_errors`` later. First, let's have a look at
how the form widget is used in the template. Here's the body contents of
``formstutorialtg2.templates.add.html``::

    <p py:content="form.display(submit_text='Add Comment')">Comment form</p>

Yep, that's all there is to it.

The ``display`` method of a widget instance emits the HTML code to display the form on your page.

Form display continued
~~~~~~~~~~~~~~~~~~~~~~

Now that you know the basics of declaring and instantiating forms, let's take
a closer look at the possibilities you have when you display the form.

The simplest way to display the form, as we just saw, is to call the forms
``display`` method::

    ${form.display()}

It's also possible to call the instance directly and get the same behavior::

    ${form()}

For our comment form, this will produce the HTML output similar to the following::

    <FORM ACTION="save" NAME="form" METHOD="post">
      <TABLE BORDER="0">
        <TR>
           <TD>
            <LABEL CLASS="fieldlabel" FOR="form_name">Name</LABEL>
            </TD>
            <TD>
              <INPUT CLASS="textfield" TYPE="text" ID="form_name" NAME="name">
            </TD>
          </TR>
          ...
          <TR>
            <TD>
            </TD>
            <TD>
              <INPUT TYPE="submit" CLASS="submitbutton">
            </TD>
          </TR>
        </TABLE>
    </FORM>

You can see that the submit button has no value and will therefore be
displayed with a language dependant default label because we didn't set the
form's ``submit_text``.

If you look at the generated FORM element, you'll also note that its
``action`` attribute is set to the value of the ``action`` argument, which we
specified when we created the form instance.

As a convenience, you can override both the ``action`` and ``submit_text``
arguments at display time::

    ${form(action="preview", submit_text='Preview Comment')}

Whether you want to specify ``action`` (or ``submit_text`` for that matter)
when you create the form or when you display it, depends on whether you are
reusing the form in another context or not and how closely coupled the form
widget and the controller methods handling the form are in your application.

If you want to preset the form field values - for instance to edit already
existing data - you pass the form values as the first argument::

    ${form(data, submit_text='Add Comment')}

You can also explicitly specify it as the ``value`` keyword argument::

    ${form(value=data, submit_text='Add Comment')}

Where ``data`` is a dictionary of the form::

    data = dict(name='Joe', comment='Hello World', notify=True, ...)

Displaying forms is nice, but it really doesn't help you out *that* much.
Admittedly, some people write entire toolkits to do just this
sort of thing (GWT, Pyjamas), but TurboGears widgets offer you more.

Form field validators
---------------------

Validation ensures that the values you're getting are the values your method
is expecting. Sometimes this is critically important, other times it's
convenient, but quite a bit of time in web programming is traditionally tied
up in displaying a form, processing the form, validating it's values, and --
in the event of errors-- redisplaying the form with the errors marked.
TurboGears widgets were created explicitly to solve this problem.

In practice, you get validation by adding validators to your widget
declarations and setting the appropriate decorators on your form handling
method. You can get super-fancy and do it `other ways`_ if necessary,
but we'll take the simple solutions for simple problems approach here.

.. _other ways: main/FormValidationWithSchemas

::

    #repeat, for convenience

    class CommentFields(WidgetsList):
        """The WidgetsList defines the fields of the form."""

        name = forms.TextField(validator=validators.NotEmpty())
        email = fomss.TextField(validator=validators.Email(not_empty=True),
          attrs={'size':30})
        comment = forms.TextArea(validator=validators.NotEmpty())
        notify = forms.CheckBox(label="Notify me")
        
If you look at the definition of ``CommentFields`` repeated above, you'll see
that there is a validator for each of the first three fields. These validators
are part of the ``formencode.validators`` package, part of
around Ian Bicking's `FormEncode`_ project. Since all values in a form are
sent as strings, validators both convert the value to the appropriate Python
type and check that the value matches a criteria in one step because one
usually requires the other. For example, if your validator requires a numeric
input be greater than 5 and you get ``"10"``, you have to convert ``"10"`` to
the int ``10`` before a meaningful comparison can be made. In this case, we're
not doing type conversion for any of our fields, but it's a useful thing to
know.

.. _FormEncode: http://www.formencode.org

The first and third fields have a ``validators.NotEmpty`` validator, which
explicitly states that they are required fields. The second field, with a
``validators.Email`` validator, is required as well.  We explicitly state this
by passing a ``not_empty=True``, but adding a validator to the field generally
makes that field required. The empty string, for example, is not a valid email
address, so the email validator will fail.  You can get validation on
non-required fields by passing an ``if_empty="default value"`` argument to the
validator's constructor.

Form Processing
---------------

Turning our attention to the ``save`` method::

    @expose()
    @validate(comment_form, error_handler=add)
    def save(self, name, email, comment, notify=False):
        """Handle submission from the comment form and save the comment."""

        comments.add(name, email, comment)
        if notify:
            flash(_('Comment added! You will be notified.'))
        else:
            flash(_('Comment added!'))
        redirect('/index')

Our method itself takes a set of arguments corresponding to the fields in the
form. Tracking large numbers of fields is very inconvenient, so it's common to
just use keyword arguments instead::

    @expose()
    @validate(comment_form, error_handler=add)
    def save(self, **data):
        comments.add(
            data['name'],
            data['email'],
            data['comment'
            data.get('notify', False)
        )
        #...

Using this syntax you get the data as a dictionary and you have to extract the
field values from there. The use of ``.get()`` above is needed for the
``notify`` field, since this is not guaranteed to be included in the data
and because there is no validator checking for its presence, while the other
fields will be present for sure if there was no validation error.


.. note:: The form handling strips off the default submit field so that you
          don't have to deal with it. If you add your own, it won't be
          stripped.

Finally, the ``flash`` method displays a confirmation notice on the next page
the user is redirected to, which is the index page with the list of comments.

Data validation
~~~~~~~~~~~~~~~

Let's take another, closer look at the ``save`` method.  Our interest now lies 
not in its contents, but rather the decorators.  We can see that the method is 
exposed without a template. It does need to be exposed or Pylons will raise 
a ``404``. The lack of a template is fine because we're going to redirect the 
user to another (output-providing) method depending on whether the input is 
valid or not.

The ``@validate()`` decorator extracts the various validators from the form,
loops through them, and throws an error if problems are found. We're `glossing
over details`_, but that's the basic idea.

.. _glossing over details: main/ValidateDecorator

If ``@validate()`` does throw an error, the ``error_handler`` method takes
care of them.  If a validation error occurs, TurboGears will store a dictionary
of FormEncode validation errors in pylons.c.form_errors.

In the example, we're re-using ``add`` so that the form will be re-displayed
if errors occur. Let's have a look at the ``add`` method again::

    @expose(template='formstutorialtg2.templates.add')
    def add(self):
        """Show the comment form."""

        if pylons.c.form_errors:
            flash('There was a problem with the form!')
        return dict(form=comment_form)

The error handling method, if desired, could look into the ``form_errors``
dictionary to see which fields validation has failed and act accordingly. In
practice, most form error handlers simply do what we do here: put up a
notification message and display the form showing the validation errors.

Conclusion
----------

In this tutorial you have learned how to create a simple form widget composed
of several form fields. You have seen how the widget is passed to the
template, displayed and how submissions from the form are handled in the
controller. You have also seen simple validators in action that simplify error
handling for forms substantially.

This tutorial only covers basic widget usage. If you'd like to know more,
explore the `widgets overview`_ and the check out the `widget browser`_ in the
`toolbox`_.

Download the example project
----------------------------

`FormsTutorial-2.0.tgz <attachment:FormsTutorial-2.0.tgz>`_

.. note:: The code for this example is courtesy of Michele Cella, but the
          individual files in the project have been updated to reflect changes
          in TurboGears versions over time and were adapted by various authors
          with respect to style, design etc.

-----

.. note:: The comment feature has been disabled on this page due to heavy spamming. If you want to comment on the contents of this page, if you have questions, or want to report an error, please write to the TurboGears `mailing list`_.

.. _mailing list: main/GettingHelp
