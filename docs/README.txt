Documentation Generation Guide
==================================

DOC Generation
--------------

Make sure that you have followed the instructions in top-level ``INSTALL.txt``
file to install TurboGears 2.

Prerequisite
------------

You also need to install Sphinx_ to generate the TurboGears documentation from
docs.turbogears.org::

    $ easy_install Sphinx

And pysvn module is required for the Wiki20 doc which pulls source code from svn.

    http://pysvn.tigris.org/project_downloads.html

Source package is here:

    http://pysvn.barrys-emacs.org/source_kits/pysvn-1.6.1.tar.gz

This may require that you have the includes for SVN.

To generate the docs you will also need:

  - Mercurial installed
  - memcache or cmemcache installed (http://gijsbert.org/downloads/cmemcache/cmemcache-0.95.tar.bz2)

Generate Doc
-------------

For the following, change to the ``docs`` directory below the top-level
TurboGears 2 source directory.

Finally, run ``make <builder>`` to generate docs::

    $ make html



Document Migration Script
--------------------------

There's a help script calls ``get_tgdoc.py`` to fetch rest docs from TurboGears wiki. Since TurboGears 2 documents are already migrated to sphinx-based document system, you don't need to use it anymore::

    $ python get_tgdoc.py


.. _sphinx: http://sphinx.pocoo.org/
.. _sourceforge: http://sourceforge.net/project/showfiles.php?group_id=32455
.. _reStructuredText: http://docutils.sourceforge.net/rst.html

