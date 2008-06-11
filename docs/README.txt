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
.. _sourceforge: http://sourceforge.net/project/showfiles.php?group_id=32455
.. _reStructuredText: http://docutils.sourceforge.net/rst.html

