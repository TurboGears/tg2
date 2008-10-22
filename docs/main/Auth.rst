Authentication and Authorization
================================

:Status: Draft


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
which should be really simple in most situations.

Such a system is made up of two components, well integrated into TurboGears:

  * `repoze.who <http://static.repoze.org/whodocs/>`_, is a TurboGears
    independent framework for ``authentication`` in WSGI applications. You
    normally don't have to care about it because by default TG2 applications
    ship all the code to set it up (as long as you had selected such an option
    when you created the project), but if you need something more advanced you
    are in the right place.
    
  * :mod:`tgext.authorization`, a TurboGears 2 specific framework for 
    ``authorization`` which is backwards compatible with the TurboGears 1 
    Identity authorization system.
    
Where would you like to store your users' credentials? In a database? LDAP?
Htaccess file? You may use the backend you want (or create your own if it
isn't available), and don't worry if you need to change it afterwards: You
would not need to touch your code! Except, of course, the snippet that tells
where the data may be found.

Regardless of the level of customization you need for the
authentication/authorization mechanisms in your applications, these documents
will help you achieve what you need.


The three pillars: Users, groups and permissions
------------------------------------------------

@TODO


Getting started, quickly
------------------------

While ``tgext.authorization`` only deals with authorization, it provides a
module to setup authentication via ``repoze.who`` so that you can get started
with authentication and authorization very quickly.

This module is called "quickstart" and stores your users' credentials, groups
and permissions in a SQLAlchemy-managed database.

The quickstart may be enabled while creating the TG2 project or afterwards,
and it may be easily replaced by another.


Using it on a new project
~~~~~~~~~~~~~~~~~~~~~~~~~

To use this just answer `yes` during the `paster quickstart` process when it
asks you if you want auth::
 
  Do you need Identity (usernames/passwords) in this project? [no] yes

You'll then get authentication and authorization code added for you. 


Implementing the quickstart on an existing project
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

@TODO: tgext.authorization's quickstart is the same as the former
tg.ext.repoze.who's middleware module.


Going beyond the quickstart
---------------------------

If you need more power than that provided by the quickstart, or if you just 
want to customize some things, you may want to read the following pages:

.. toctree::
    :maxdepth: 2

    Auth/Authentication
    Extensions/Authorization/index
