##This is an official page. Only editors and admins can change it.



Contributing to TurboGears
==========================

:status: Official

.. contents::
    :depth: 2

If you want to help out, we want to help you help out! The goal of this 
document is to help you get started and answer any questions you might 
have. The `Project Philosophy`_ document has a more high-level view, 
whereas this document is nuts-and-bolts. The `TurboGears team <TurboGearsTeam>`_
page lists who is responsible for what.


Subversion
----------

The TurboGears subversion repository is at http://svn.turbogears.org/.

You can also browse the repository via the `TurboGears Trac`_.

.. _TurboGears Trac: http://trac.turbogears.org/browser

TurboGears 2 development is currently occurring in the trunk.

Note that the trunk may break at any time so don't run it unless you know what 
you are doing.

To check out the tg2 code, you would typically use the command::

   svn co http://svn.turbogears.org/trunk turbogears

This will give you a "turbogears" directory with the trunk in it.


You can get the basic Subversion clients from `the official Subversion 
site`_, and graphical clients are available for just about any platform. 
The `Version Control with Subversion`_ book is available for reading 
online.

.. _the official Subversion site: http://subversion.tigris.org/
.. _Version Control with Subversion: http://svnbook.red-bean.com/


Before you finish setting up the TurboGears 2 development environment with `setup.py develop` you will need to download and install a current version of Pylons from their mercurial repository. 

Installing Pylons from Source via Mercurial:
------------------------------------------------

Pylons uses the Mercurial Version control system, so you probably need to install Mercurial before you can pull down the latest development source for Pylons. Mercurial `packages are available <http://www.selenic.com/mercurial/wiki/index.cgi/BinaryPackages>`_ for Windows, Mac OSX, and other OS's.

First you need to install:

1. Python (see http://www.python.org)

2. setuptools (run http://peak.telecommunity.com/dist/ez_setup.py from any directory)

Now you can check out the latest code::

 $ hg clone http://pylonshq.com/hg/pylons-dev Pylons

To tell setuptools to use the version you are editing in the Pylons directory::

 $ cd Pylons 
 $ python setup.py develop


Now you can make changes to the files in the Pylons directory and the code will run exactly as if you had installed a version of the egg with the changes you have made.

Developing with eggs
--------------------

Now that the Pylons dependency is filled you should be able to finish 
installing the rest of the dependecies you need by telling setuptools 
to automatically fetch the eggs for you. 

TurboGears (and even projects that TurboGears creates via quickstart) 
uses setuptools_ to make packaging and distribution much easier.

.. _setuptools: http://peak.telecommunity.com/DevCenter/setuptools

To start developing on TurboGears itself, you'll want to go into your 
checked-out copy and run::

    python setup.py develop

That command tells setuptools that you're going to be using that code 
for TurboGears, rather than any installed TurboGears egg you might have.


Dealing with Dependencies
-------------------------

It is not uncommon between releases of TurboGears that projects used by 
TurboGears will be upgraded. For the core projects used by TurboGears, 
there are ``svn:externals`` defined to check out the appropriate version 
of the projects in the thirdparty directory. When projects are upgraded, 
the setup.py file is also changed to reflect the new version that is 
required to use TurboGears.

If you get an error about a requirement not being met when running a 
development copy of TurboGears, you will generally be able to satisfy the
requirement by going into the thirdparty directory and running::

  python -c "import setuptools; execfile('externals.py')" develop

Alternatively, you can run::

  easy_install .

which will give you a snapshot installation that doesn't track each svn 
update.

If you plan to make changes to one of the projects that TurboGears uses, 
make sure that you've got Subversion pointing to an appropriate version 
of that project for making changes (often the trunk). With the correct 
version in place, you can run "``python setup.py develop``" in that 
project to start using the development version of that tool.


.. note:: On the Linux/Mac OS X platform you have to copy the
    'tg-admin' (in ``python/bin/``) command to ``/usr/local/bin``
    manually to replace the old one. You can execute
    ``tg-admin info`` to check whether the version is correct or not.


Coding style
------------

Since it's hard to argue with someone who's already written a code style 
document, TurboGears will follow `PEP 8`_ conventions.

To ensure that files in the TurboGears source code repository have proper 
line-endings, you must configure your Subversion client. Please see
the `patching guidelines`_ for details.

.. _PEP 8: http://www.python.org/peps/pep-0008.html


Testing
-------

Automated unit tests are better than good. They make future growth of the
project possible.

TurboGears uses Nose_, which makes testing easy. To get going with Nose, 
just run::

  easy_install nose

.. _Nose: http://somethingaboutorange.com/mrl/projects/nose/

(As with all ``easy_install`` commands, you may need to use the ``--
script-dir`` option to tell it where to put the command line tool and you
may need to use "``sudo``" on Unix-like systems to access that directory.)

Once installed, you can run the TurboGears tests just by running::

  nosetests

The ``turbogears.testutil`` package includes some utility functions and 
classes that make you're life easier as you're trying to test.


Documentation
-------------

As mentioned in the `Project Philosophy`_ document, a feature doesn't 
truly exist until it's documented. Tests can serve as good documentation,
because you at least know that they're accurate. But, it's also nice to 
have some information in English.

.. _Project Philosophy: 1.0/Philosophy

There are two kinds of docs, and both have their useful place:

**API reference**

    A modified epydoc_ (which includes links to the source) is used to
    generate API docs for the website. It's not very taxing at all to add
    these doc strings as you work on the code. See the
    `API reference for version 1.0 <1.0/API>`_ here.

.. _epydoc: http://epydoc.sourceforge.net/


**Manual**

    The TurboGears documentation is maintained on the
    `docs.turbogears.org`_ wiki. If you want to work on the documentation
    in the wiki, please read the `guidelines for contributing 
    documentation`_.

.. _docs.turbogears.org : http://docs.turbogears.org/
.. _guidelines for contributing documentation: DocHelp

When you contribute a new doc in the wiki, please write a page in the 
appropriate RoughDocs section of the site (e.g. for TurboGears version 
1.1, you'd link it up from1.1/RoughDocs). One of the documentation
editors will then pull your document into the official documentation, 
possibly doing a bit of editing in the process so that the style and
tone match the rest of the official documents.

Please document your own work. It doesn't have to be Shakespeare, but 
the editors don't enjoy writing documentation any more than you do (we'd 
rather be coding) and it's much easier to edit an existing doc than it is
to figure out your code and write something from scratch.


Documenting Changes
-------------------

The Trac_ is mostly used for tracking upcoming changes and tasks required
before release of a new version. The changelog_ provides the human 
readable list of changes.

.. _trac: http://trac.turbogears.org/
.. _changelog: http://trac.turbogears.org/turbogears/file/trunk/CHANGELOG.txt

Updating the changelog right before a release just slows down the release. Please 
**update the changelog as you make changes**, and this is **especially** critical 
for **backwards incompatibilities**.


How to Submit a Patch
---------------------

Please make sure that you read and follow the `patching guidelines`_.


-----

.. note:: The comment feature has been disabled on this page due to heavy
    spamming. If you want to comment on the contents of this page, if you 
    have questions, or want to report an error, please write to the 
    TurboGears `mailing list`_.
