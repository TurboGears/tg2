Documentation Generation Guide
==================================

DOC Generation
--------------

Make sure that you have followed the instructions in top-level ``INSTALL.txt``
file to install TurboGears 2.

You also need to install Sphinx_ to generate the TurboGears documentation from
docs.turbogears.org::

    $ easy_install Sphinx

For the following, change to the ``docs`` directory below the top-level
TurboGears 2 source directory.

Then run ``get_tgdoc.py`` script to fetch rest docs from TurboGears wiki::

    $ python get_tgdoc.py

Finally, run ``make <builder>`` to generate docs::

    $ make html

.. _sphinx: http://sphinx.pocoo.org/


API Generation
--------------

You need to install epydoc_ 3 first to generate the TurboGears API
documentation from the source code.

You can either download a release from pypi::

    $ easy_install -U epydoc

or get the epydoc_ source from epydoc's SVN repository::

    $ svn co https://epydoc.svn.sourceforge.net/svnroot/epydoc/

Follow the documentation on the epydoc web site to install it.


Checking for missing doc strings
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To check which docs need to be written, use the following command in the
top directory of the TurboGears trunk source::

    $ epydoc --check tg

The command will check that every module, class, method, and function has a
description; that every parameter has a description and a type; and that every
variable has a type. It will list those that don't meet these requirements.


Generating HTML docs
~~~~~~~~~~~~~~~~~~~~

Use this command in the top directory::

    $ epydoc --config setup.cfg

to generate the TurboGears 2 API documentation in the ``apidocs`` folder.

You can change the settings in the file ``setup.cfg`` in the main folder
to customize the output.


Writing docs
~~~~~~~~~~~~

.. note:: The TurboGears project uses reStructuredText_ format for doc strings.

It's a bit different from epydoc's default format. Check the documentation
about using reStructuredText with epydoc on the epydoc web site:

* http://epydoc.sourceforge.net/manual-docstring.html
* http://epydoc.sourceforge.net/manual-othermarkup.html
* http://epydoc.sourceforge.net/manual-fields.html


Debugging docs
~~~~~~~~~~~~~~

If you get a formatting error and want to locate the position in the source
quickly, use the verbose mode of epydoc by supplying the ``-v`` option::

    $ epydoc --config setup.cfg -v


.. _epydoc: http://epydoc.sourceforge.net/
.. _sourceforge: http://sourceforge.net/project/showfiles.php?group_id=32455
.. _reStructuredText: http://docutils.sourceforge.net/rst.html

