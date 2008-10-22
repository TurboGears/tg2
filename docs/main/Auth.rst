Authentication and Authorization in TurboGears 2
================================================

:Status: Official

This documents describes how to implement authentication and authorization in
TG 2 applications. Although there are other ways to implement it (e.g., using
the `AuthKit <http://authkit.org/>`_ package or a project-specific solution), 
this document only describes the officially supported and recommended way.


Overview
--------

``Authentication`` is the act verifying that somebody is really who she claims 
to be, which is normally done using credentials (e.g., when you need to access
your email, you provide the email address and your password, or if you want
to check your bank account, you'll probably have to provide you Id number and
your card's ping). In other words, finding `who` you are.

``Authorization``, on the other hand, is the act of granting access to given
resources depending on who would use them. For example, allowing registered
members to leave comments on a blog, or allowing your friends to see your
pictures while others cannot. In other words, finding `what` you may do.

TurboGears 2 applications may take advantage of a robust, extendable, pluggable 
and easy-to-use system for authentication and authorization suitable for nearly 
all situations — in fact, you may extend it to suite your needs if it doesn't, 
which should be really simple in most situations. Such a system is made up of 
two components, well integrated into TurboGears:

  * :mod:`repoze.who`, a TurboGears-independent framework for 
    ``authentication`` in WSGI applications. You normally don't have to care 
    about it because by default TG2 applications ship all the code to set it up
    (as long as you had selected such an option when you created the project), 
    but if you need something more advanced you are in the right place.
  * :mod:`tgext.authorization`, a TurboGears 2 specific framework for 
    ``authorization`` which is backwards compatible with the TurboGears 1 
    Identity authorization system.

You may store your users' credentials where you want (e.g., in a database, an
LDAP server, an Htaccess file) and also store your authorization settings
in any type of source (e.g., in a database, Ini file) -- if the back-end you
need is not available, you may create it yourself (which is usually very easy). 
And don't worry if you need to change the back-end afterwards: You would not 
need to touch your code! Except, of course, the snippet that tells where the 
data may be found.


The three pillars: Users, groups and permissions
------------------------------------------------

Authorization in TurboGears 2 applications uses a common pattern based on
the ``users`` (authenticated or anonymous) of your web application, the 
``groups`` they belong to and the ``permissions`` granted to such groups. But
you can extend it to check for other conditions (such as checking that the
user comes from a given country, based on her IP address, for example).

The authentication framework (:mod:`repoze.who`) only deals with the 
:term:`source` (or sources) that handle your users' credentials, while the 
authorization framework (:mod:`tgext.authorization`) deals with both the 
source(s) that handle your groups and those that handle your permissions.


Getting started, quickly
------------------------

While :mod:`tgext.authorization` only deals with authorization, it provides a
module to setup authentication via :mod:`repoze.who` so that you can get started
with authentication and authorization very quickly. It may be enabled while 
creating the TG2 project or afterwards, and it may be easily replaced by a 
custom solution.

To use it on a new projet, just answer "yes" during the `paster quickstart` 
process when it asks you if you want auth::
 
  Do you need authentication and authorization in this project? [yes]

You'll then get authentication and authorization code added for you, including
the SQLAlchemy-powered model definitions and the relevant settings in
``{yourpackage}.config.app_cfg``. It also defines the default users, groups and
permissions in ``{yourpackage}.websetup``, which you may want to customize. 

Before trying to login and try authorization with the rows defined in
``{yourpackage}.websetup``, you have to create the database; run the following
command from your project's root directory::

    paster setup-app

.. note::
  This module is :mod:`tgext.authorization.quickstart` and only works if your 
  users' credentials, groups and permissions are stored in a `SQLAlchemy 
  <http://www.sqlalchemy.org/>`_-managed database. To implement it on an 
  existing project, or customize the model structure assumed by it, you have to
  read the documentation for :mod:`tgext.authorization.quickstart`.


Going beyond the quickstart
---------------------------

If you need more power than that provided by the quickstart, or if you just 
want to customize some things, you may want to read the following pages:

.. toctree::
    :maxdepth: 2

    Auth/Authentication
    Extensions/Authorization/index
