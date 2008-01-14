API Documentation Generation Guide
==================================

You need to install epydoc_ 3 first to generate the TurboGears API 
documentation from the source code.

You can either download a beta release from sourceforge_ or get the epydoc source from epydoc's SVN repository::

    $ svn co https://epydoc.svn.sourceforge.net/svnroot/epydoc/

Follow the documentation on the epydoc web site to install it.


Checking for missing doc strings
--------------------------------

To check which docs need to be written, use the following command in the 
top directory of the TurboGears trunk source::

    $ epydoc --check tg

The command will check that every module, class, method, and function has a description; that every parameter has a description and a type; and that every variable has a type. It will list those that don't meet these requirements.


Generating HTML docs
--------------------

Use this command in the top directory::

    $ epydoc --config setup.cfg

to generate the TurboGears 2 API documentation in the ``apidocs`` folder.

You can change the settings in the file ``setup.cfg`` in the main folder 
to customize the output.


Writing docs
------------

.. note:: The TurboGears project uses reStructuredText_ format for doc strings.

It's a bit different from epydoc's default format. Check the documentation
about using reStructuredText with epydoc on the epydoc web site:

* http://epydoc.sourceforge.net/manual-docstring.html
* http://epydoc.sourceforge.net/manual-othermarkup.html
* http://epydoc.sourceforge.net/manual-fields.html


Debugging docs
--------------

If you get a formatting error and want to locate the position in the source
quickly, use the verbose mode of epydoc by supplying the ``-v`` option::

    $ epydoc --config setup.cfg -v


.. _epydoc: http://epydoc.sourceforge.net/
.. _sourceforge: http://sourceforge.net/project/showfiles.php?group_id=32455
.. _reStructuredText: http://docutils.sourceforge.net/rst.html
