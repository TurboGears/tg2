

TurboGears2 Installation Guide
===============================

.. Note:: At current stage TurboGears2 is available testing by developers who are willing to use Subversion to track the latest changes. 

Requirements
------------

While in Development there are several dependencies: 

 * Python, version >= 2.4.
   + Please keep in mind, that for RPM-based systems you will also need
   python-devel and python-xml packages.
 * Pylons Trunk checkout. We require the development version right now.  We will depend on 0.9.6 when it is released.


Installing TurboGears2
-----------------------

The command:

  $ python ./setup.py develop

will byte-compile the python source code and tell setuptools to use it from your subversion checkout directory. .

So, the general process is to check out pylons, install it with  setup.py  develop.

If you don't already have the turbogears and pylons source, you can  get them from svn::

    $ svn co http://pylonshq.com/svn/Pylons/trunk pylons
    $ svn co http://svn.turbogears.org/trunk tg2

and install TurboGears 2 in development mode::

    $ python ./pylons/setup.py develop
    $ python ./tg2/setup.py develop
    
Update the source 
-----------------

To update the source to the current develop version. Enter the tg2 folder and type the command::

    $ svn update
    $ python setup.py develop
 
Creating a Quickstart Project
------------------------------

TurboGears2 is built on Pylons and share pylons' "paster" commands.
Enter command::

    $ paster --help
 
to get the availble command list.

The command::

    $ paster quickstart tutorial

will generate the "tutorial" package based on quickstart templates for you.

 
Running the Demo 
-----------------

Enter the tutorial folder and type::
 
    $ paster serve development.ini
 
Browse http://127.0.0.1:8080 for demo.
