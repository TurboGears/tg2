Document generation Guide
=========================

You need to install epydoc 3 first before go through this doc.

You could got epydoc source from epydoc svn::

    $ svn co https://svn.sourceforge.net/svnroot/epydoc

And follow epydoc's doc to install it.

Check Modules
-------------

To check what docs need to be written, use the command in source folder::

    $ epydoc --check tg

The command will gather all undocumented and no description python methods.

Generate Docs
-------------

To generate Turbogears2 API, use the command in source folder::

    $ epydoc --config doc/doc.ini 

to generate API documents into tg2/apidoc folder.

You could custom the doc.ini setting to generate other type of docs.

Write Docs
----------

Check docs about reStructuredText format.

http://epydoc.sourceforge.net/manual-docstring.html
http://epydoc.sourceforge.net/manual-othermarkup.html
http://epydoc.sourceforge.net/manual-fields.html

Debug Docs
-----------

To find where the format error is, use command::

    $ epydoc --config doc/doc.ini -v