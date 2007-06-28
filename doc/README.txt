Document generation Guide
=========================

You need to install epydoc 3 first before go through this doc.

Check Modules
-------------

To check what docs need to be written, use the command in tg2 folder::

    $ epydoc --check

The command will gather all undocumented and no description python methods.

Generate Docs
-------------

To generate Turbogears2 API, enter the tg2/doc folder, and use the command::

    $ epydoc --config doc.ini 

to generate API documents into tg2/apidoc folder.

You could custom the doc.ini setting to generate other type of docs.