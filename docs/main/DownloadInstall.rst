.. highlight:: bash

How to install TurboGears 2
===========================

Installing TurboGears 2 has been made simple with the advent of the package 
index.  We recommend installing TurboGears 2 into a virtual environment
so that any existing packages will not interfere with your installation, and 
so that you don't upgrade any python libraries that your system needs.  

So, with a virtual environment the basic installation goes as follows:

1. Install ``setuptools``

2. Install ``virtualenv``

3. Create a ``virtualenv`` for your project

4. Switch to the ``virtualenv``

5. ``easy_install`` TurboGears development package

6. Profit


Prerequisites
--------------

* Python 2.4 or 2.5
* Appropriate python development package (python*-devel python*-dev)

Setting up setuptools:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

On windows: 

download http://peak.telecommunity.com/dist/ez_setup.py and then run it from 
the command line.

On unix: 

If you have curl or  wget installed you can do this with a single command: 

.. code-block:: bash

	$ curl http://peak.telecommunity.com/dist/ez_setup.py | sudo python

Setting up a Virtual Environment
---------------------------------

First, install ``virtualenv`` using this command:

On Windows::

    easy_install virtualenv

On Unix: 

You will likely need root permissions to install virtualenv in you your system's  
site-packages directory: 

.. code-block:: bash

	$ sudo easy_install virtualenv

will output something like:

.. code-block:: text

    Searching for virtualenv
    Reading http://pypi.python.org/simple/virtualenv/
    Best match: virtualenv 1.1
    Downloading http://pypi.python.org/packages/2.5/v/virtualenv/virtualenv-1.1-py2.5.egg#md5=1db8cdd823739c79330a138327239551
    Processing virtualenv-1.1-py2.5.egg
    .....
    Processing dependencies for virtualenv
    Finished processing dependencies for virtualenv

Create a virtual environment:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash
	
	$ virtualenv --no-site-packages tg2env

that produces something like this::

     Using real prefix '/usr/local'
     New python executable in tg2env/bin/python
     Installing setuptools............done.

.. code-block:: bash

	$ cd tg2env

.. code-block:: bash
	
	$ source bin/activate

and now your prompt should look something like this (if you're on unix)::

	(tg2env)usrname@host:tgenv$

Install Turbogears 2
---------------------

We've included pre-compiled binaries for windows users, but if you're on unix
you'll need a working version of the GCC compiler installed, as well as the 
python headers.   On OSX this means installing Xcode (available on the OS X cd
or at http://developer.apple.com/tools/xcode/), and on Debian derived linux 
versions this requires python-dev (available via ``apt-get install python-dev``), 
Fedora users will need the python-devel rpm, etc. 

If you've got the compilers and python header files, you'll be able to install 
the latest version of turbogears via:  

.. code-block:: bash

	$ easy_install -i http://www.turbogears.org/2.0/downloads/current/index tg.devtools

A whole bunch of packages should download.  (This may take a several min.)

Validate the installation:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To check if you installed TurboGears 2 correctly, type

.. code-block:: bash
	
	$ paster --help

should look something like::

    Usage: paster [paster_options] COMMAND [command_options]

    Options:
      --version         show program's version number and exit
      --plugin=PLUGINS  Add a plugin to the list of commands (plugins are Egg
                        specs; will also require() the Egg)
      -h, --help        Show this help message

    Commands:
      create       Create the file layout for a Python distribution
      help         Display help
      make-config  Install a package and create a fresh config file/directory
      points       Show information about entry points
      post         Run a request for the described application
      request      Run a request for the described application
      serve        Serve the described application
      setup-app    Setup an application, given a config file

    TurboGears2:
      quickstart   Create a new TurboGears 2 project.
      tginfo       Show TurboGears 2 related projects and their versions


and you'll see a new "TurboGears2" command section in paster help.

Paster has replaced the old tg-admin command, and most of the tg-admin commands have now been reimplemented as paster commands. For example, "tg-admin quickstart" command has changed to "paster quickstart" command, and "tg-admin info" command has changed to "paster tginfo" command.

Be sure to check out our `What's new in TurboGears 2.0 <WhatsNew.html>`_ page to get a picture of what's changed in TurboGears2 so far.

Special Considerations:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cygwin** does not include the necessary binary file **sqlite3.dll**; if you want to run cygwin you'll need to install a different database. If you have cygwin installed and you want to use the default setup described here, you must perform all operations, including setup operations, within DOS command windows, not cygwin command windows.


Installing the development version of Turbogears 2 (from source)
-------------------------------------------------------------------

Installing Pylons from Source:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

Installing TurboGears 2 from Source:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

TurboGears 2 are constructed by a bunch of packages.

Check out the latest code from subversion::

 $ cd ..
 $ svn co http://svn.turbogears.org/projects/tg.devtools/trunk tgdev
 $ svn co http://svn.turbogears.org/trunk tg2
 $ svn co http://tgtools.googlecode.com/svn/projects/tg.ext.repoze.who/trunk tg.ext.repoze.who

- tgdev is a set of tools, paster command plugins to create default template, admin interface, and migrations.
- tg2 package is TurboGears 2 core.
- tg.ext.repoze.who is an extension for tg2 that aims to provide an API compliant implementation of the old tg1 identity framework.


Then you repeat the same steps to tell setuptools/python to use the new tg2 installation.

Install tg.ext.repoze.who::

 $ cd tg.ext.repoze.who
 $ easy_install Paste
 $ easy_install zope.interface
 $ python setup.py develop

Install TurboGears 2 server::

 $ cd ..
 $ cd tg2
 $ easy_install PasteScript==dev
 $ easy_install genshi
 $ python setup.py develop

Install TurboGears 2 developer tools::

 $ cd ..
 $ cd tgdev
 $ python setup.py develop

Then you have installed TurboGears 2.

.. note:: if you have installed old dependency packages, you could remove 
   them from {python_path}/site-packages/easy-install.pth



Troubleshooting
----------------

It is possible (but not likely) you might see a few other error messages.  
Here are the correct way to fix the dependency problems so things will install 
properly.

If you get an error about ``ObjectDispatchController`` this means your Pylons 
installation is out-of-date. Make sure it's fresh ("hg pull -u" or "hg pull" 
followed by hg update -- alternatively you can create a brand new Pylons 
branch in a new directory with "hg clone").

When installing on Mac OSX, if you get an error mentioning "No local packages 
or download links found for RuleDispatch", you can try the solution posted to 
the `ToscaWidgets discussion list 
<http://groups.google.com/group/toscawidgets-discuss/browse_thread/thread/cb6778810e96585d>`_, 
which advises downloading it directly::

 $ sudo easy_install -U -f http://toscawidgets.org/download/wo_speedups/ RuleDispatch

If you get the following error when starting a project with ``paster serve``::

 AttributeError: 'WSGIRequest' object has no attribute 'accept_language'

update your Pylons checkout with ``hg update`` and try again.

If ``python setup.py develop`` gives you::

 Traceback (most recent call last):
   File "setup.py", line 3, in <module>
     from ez_setup import use_setuptools


... commenting out the first two lines in setup.py seems to work.  See 
`this discussion <http://groups.google.com/group/pylons-discuss/browse_thread/thread/1ccf9366004c8e11>`_


If you get this error about webhelpers, you need the latest version from 
mercurial::

  $ hg clone https://www.knowledgetap.com/hg/webhelpers
  $ cd webhelpers
  $ python setup.py develop
