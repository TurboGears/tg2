= Equivalent imports =

You (may) need to `easy_install twForms` explicitly to access toscawidgets.forms.

||TG1                                       ||TG2                                     ||
||from turbogears import *                  ||from tg import *                        ||
||from turbogears.widgets import WidgetsList||from toscawidgets.api import WidgetsList||
||from turbogears.widgets import TableForm  ||from toscawidgets.forms import TableForm||
||from turbogears.widgets import TextField  ||from toscawidgets.forms import TextField||
||from turbogears import validators         ||from formencode import validators       ||

= Kid to Genshi =

In Kid, py:attrs would accept a series of `x=y` statements as a string, like

{{{
  <a py:content="the page" py:attrs="href=thepage.html">link</a>
}}}

In Genshi, py:attrs should be given a dict:

{{{
  <a py:content="the page" py:attrs="{'href':'thepage.html'}">link</a>
}}}
