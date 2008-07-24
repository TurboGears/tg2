

Creating ToscaWidgets Libraries
===============================


Paster
------

Paster is a tool which creates a set of boiler-plate scripts akin to an egg package which you can then build your library inside of.

Use paster to create your own toscapackage. ::

  paster create -t toscawidgets tw.mypackagename

This will create a toscawidgets package with the name
tw.mypackagename.  The directory structure looks like this ::

 tw.mypackagename/
 |-- setup.cfg
 |-- setup.py
 |-- tests
 |   |-- __init__.py
 |   `-- test_widget.py
 |-- toscawidgets
 |   |-- __init__.py
 |   |-- __init__.pyc
 |   `-- widgets
 |       |-- __init__.py
 |       |-- __init__.pyc
 |       `-- mypackage
 |           |-- __init__.py
 |           |-- release.py
 |           |-- samples.py
 |           |-- static
 |           `-- widgets.py
 `-- tw.mypackagename.egg-info
     |-- PKG-INFO
     |-- SOURCES.txt
     |-- dependency_links.txt
     |-- entry_points.txt
     |-- namespace_packages.txt
     |-- not-zip-safe
     |-- paster_plugins.txt
     |-- requires.txt
     `-- top_level.txt 


Now you need to cd into your new package's directory and install it so you can inport it in your application. ::

 cd tw.mypackagename
 python setup.py develop

If you are interested in participating in tw.tools you should follow the standard package name which is tw. followed by your package name in all lower case letters.

At this point it is a good idea to modify the setup.py file to add in dependencies on other
public/private packages.

Finally, modify the toscawidgets/widgets/widgets.py to create your
widget(s).

your imports will look something like::

  from tw.mypackagename import mywidgetname

testing your widget
-------------------

Put a test for your widget in the test_widgets.py file.

tw.tools
--------
tw.tools (and soon to be toscawidgets.org) gives you an easy place to share and publish your widget code.  Simply create a widget package, and notify the toscawidgets board that you are interested in sharing.  We will give you access to http://twtools.googlecode.com and give your package a trunk/tags/branches hierarchy.  You can decide to create your own releases, or have us generate releases for you and publish them to PyPI.


WidgetBrowser
-------------

At some point we will add the capability to let the widget browser know how to instantiate a test-version of your widget and display it so that it can be integrated with toscawidgets.org
