How to install TurboGears 2
=============================

Installing TurboGears 2 currently requires you to be willing to checkout both the Pylons and TurboGears 2 code from their respective version control systems.  TurboGears 2 is working well, and there is at least one large project built upon it already, but it's not yet documented and ready for users who aren't ready to deal with the current rate of change in the project.

We do expect to have a technology preview release sometime soon, and that should provide a clear picture of the TurboGears 2 stack, and a slightly more stable API.   However, if you want API stability and good documentation, you may want to consider building your application on TurboGears 1 and porting it to TG2 after it is officially released.

Prerequisites:
-----------------------
* gcc
* python
* appropriate python development package (python*-devel python*-dev)

Installing Pylons:
-----------------------

You could easy_install pylons with command::

 $ easy_install -f http://pylonshq.com/download/0.9.7 -U Pylons

Installing Pylons from Source:
--------------------------------

.. note:: If you've installed pylons in previous section, you could skip to next section.

Pylons uses the Mercurial Version control system, so if you want to install from repository,  you probably need to install Mercurial before you can pull down the latest development source for Pylons. Mercurial `packages are available <http://www.selenic.com/mercurial/wiki/index.cgi/BinaryPackages>`_ for Windows, Mac OSX, and other OS's.

First you need to install:

1. Python (see http://www.python.org)

2. setuptools (run http://peak.telecommunity.com/dist/ez_setup.py from any directory)

Now you can check out the latest code::

 $ hg clone http://pylonshq.com/hg/pylons-dev Pylons


To tell setuptools to use the version you are editing in the Pylons directory::

  $ cd Pylons
  $ python setup.py develop


**Mac OSX Leopard** comes with Python 2.5 but does not include **setuptools**. Install it using the instructions above.

**Cygwin** does not include the necessary binary file **sqlite3.dll**; if you want to run cygwin you'll need to install a different database. If you have cygwin installed and you want to use the default setup described here, you must perform all operations, including setup operations, within DOS command windows, not cygwin command windows.

Now you can make changes to the files in the Pylons directory and the code will run exactly as if you had installed a version of the egg with the changes you have made.

Installing Paver:
-----------------------

To install paver::

 $ easy_install Paver


Installing TurboGears 2 from Source:
--------------------------------------

TurboGears 2 are constructed by a bunch of packages.

Check out the latest code from subversion::

 $ cd ..
 $ svn co http://svn.turbogears.org/projects/tg.devtools/trunk tgdev
 $ svn co http://svn.turbogears.org/trunk tg2
 $ svn co http://svn.turbogears.org/projects/tgrepozewho/trunk tgrepozewho

tg2 package is TurboGears 2 core. Others are paster command plugins to create default template, admin interface, and migrations.

Then you repeat the same steps to tell setuptools/python to use the new tg2 installation.

Install tgrepozewho::

 $ cd tgrepozewho
 $ python setup.py develop

Install TurboGears 2 server::

 $ cd ..
 $ cd tg2
 $ python setup.py develop

Install TurboGears 2 developer tools::

 $ cd ..
 $ cd tgdev
 $ python setup.py develop

Then you have installed TurboGears 2.

 .. note:: if you have installed old dependency packages, you could remove them from::

 {python_path}/site-packages/easy_install.pth


Validate the installation:
----------------------------

To check if you installed TurboGears 2 correctly, type::

 $ paster --help

and you'll see a new "TurboGears2" command section in paster help.

Paster has replaced the old tg-admin command, and most of the tg-admin commands have now been reimplemented as paster commands. For example, "tg-admin quickstart" command has changed to "paster quickstart" command, and "tg-admin info" command has changed to "paster tginfo" command.

Be sure to check out our `What's new in TurboGears 2.0 <WhatsNew.html>`_ page to get a picture of what's changed in TurboGears2 so far.

Troubleshooting
----------------

If you get an error about ``ObjectDispatchController`` this means your Pylons installation is out-of-date. Make sure it's fresh ("hg pull -u" or "hg pull" followed by hg update -- alternatively you can create a brand new Pylons branch in a new directory with "hg clone").

When installing on Mac OSX, if you get an error mentioning "No local packages or download links found for RuleDispatch", you can try the solution posted to the `ToscaWidgets discussion list <http://groups.google.com/group/toscawidgets-discuss/browse_thread/thread/cb6778810e96585d>`_, which advises downloading it directly::

 . $ sudo easy_install -U -f http://toscawidgets.org/download/wo_speedups/ RuleDispatch
If you get the following error when starting a project with ``paster serve``::

 . AttributeError: 'WSGIRequest' object has no attribute 'accept_language'
update your Pylons checkout with ``hg update`` and try again.

If ``python setup.py develop`` gives you::

 . Traceback (most recent call last):
  . File "setup.py", line 3, in <module>
   . from ez_setup import use_setuptools


... commenting out the first two lines in setup.py seems to work.  See `this discussion <http://groups.google.com/group/pylons-discuss/browse_thread/thread/1ccf9366004c8e11>`_

It is possible you might see a few other error messages.  Here are the correct way to fix the dependency problems so things will install properly.

If you get this error about PyProtocols::

   error: Could not find suitable distribution for Requirement.parse('PyProtocols>=1.0a0dev-r2302')

Then do this::

  $ wget http://dbsprockets.googlecode.com/files/PyProtocols-1.0a0dev-r2302.zip
  $ unzip PyProtocols-1.0a0dev-r2302.zip
  $ cd PyProtocols-1.0a0dev-r2302
  $ python setup.py develop


If you get this error about RuleDispatch::

  error: Could not find suitable distribution for Requirement.parse('RuleDispatch>=0.5a0.dev-r2306')

Then you need to do the following::

  $ cd ..
  $ wget http://dbsprockets.googlecode.com/files/RuleDispatch-0.5a0.dev-r2306.tar.gz
  $ tar xzf RuleDispatch-0.5a0.dev-r2306.tar.gz
  $ cd RuleDispatch-0.5a0.dev-r2306
  $ python setup.py develop

If you get this error about webhelpers, you need the latest version from mercurial::

  $ hg clone https://www.knowledgetap.com/hg/webhelpers
  $ cd webhelpers
  $ python setup.py develop
