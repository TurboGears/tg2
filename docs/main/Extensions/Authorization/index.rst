Authorization in TurboGears 2 with tgext.authorization
======================================================

:Status: Work in progress


Overview
--------

``tgext.authorization`` is an `authorization framework` for TurboGears 2,
based on `repoze.who` (which deals with `authentication`).

On one hand, it enables an authorization system based on the groups to which
the `authenticated or anonymous` user belongs and the permissions granted to 
such groups by loading these groups and permissions into the request on the way 
in to TurboGears. It also provides some decorators that check permissions for 
you, which have the same API as the TurboGears 1 identity module.

And on the other hand, it enables you to manage your groups and permissions
from the application itself or another TurboGears extension, under a backend
independent API. Among other things, this means that it will be easy for you
to switch from one backend to other, and even use this framework to migrate the
data.


Terminology
-----------

Because you may store your groups and permissions where you would like to, not
only in a database, ``tgext.authorization`` uses a generic terminology:

  * ``Source``: Where authorization data (groups and/or permissions) is stored.
    It may be a database or a file (an Htgroups file, an Ini file, etc), for
    example. 
  * ``Group source``: A `source` that stores groups. For example, an Htgroups
    file or an Ini file.
  * ``Permission source``: A `source` that stores permissions. For example, an
    Ini file.
  * ``Source adapter``: An object that manages a given type of source to add,
    edit and delete entries under an API independent of the source type.
  * ``Section``: Sections are the groups that make up a source -- this is, in a
    `permission source`, the sections are the permissions, and in a `group 
    source`, the sections are the groups.
  * ``Item``: The elements that are contained in a section. In a `permission
    source`, the items are the groups that are granted the permission 
    represented in their parent section; likewise, in a `group source`, the
    items are the Ids of the users that belong to the group represented in the
    parent section.

In your TurboGears 2 applications you may use any amount of group and 
permission sources.

Sample sources
~~~~~~~~~~~~~~
Below are the contents of a mock ``.htgroups`` file that defines the groups of 
your TG2 application. In other words, such a file is a ``group source`` of type
``htgroups``::

    developers: rms, linus, guido
    admins: rms, linus
    users: gustavo, maribel
    
And below are the contents of a mock ``*.ini`` file that defines the permissions
of the groups in your TG2 application. In other words, such a file is a 
``permission source`` of type ``Ini``::

    [manage-site]
    admins
    [release-software]
    developers
    [add-users]
    admins
    developers
    [contact-us]
    users

If you use a database to store your users, groups and permissions, then such a
database is both the group and permission source:

  * The tables where you store your groups and users are the sections and the
    section items, respectively, of the group source. They form a many-to-many
    relationship in which the children of a group (aka "section") are the
    users (aka "items") that belong to the group/section, and the children of
    a user are the groups she belongs to.
  * The tables where you store your permissions and groups are the sections and 
    the section items, respectively, of the permission source. They form a 
    many-to-many relationship in which the children of a permission (aka 
    "section") are the group (aka "items") that are granted the permission, and
    the children of a group are the permissions granted to the group.


Implementing authorization
--------------------------
@TODO: Improve these contents.

You then write code like this to require authorization::

   from tgext.authorization import authorize


Action-level authorization
~~~~~~~~~~~~~~~~~~~~~~~~~~
@TODO: Improve these contents.

Add the following methods to your controllers.root:RootController class::

    @expose('whotg.templates.about')
    @authorize.require(authorize.has_permission('manage'))
    def manage_permission_only(self, **kw):
        return dict(now=now, page='about')
    
    @expose('whotg.templates.about')
    @authorize.require(authorize.is_user('editor'))
    def editor_user_only(self, **kw):
        return dict(now=now, page='about')

    @expose('whotg.templates.login')
    def login(self, **kw):
        came_from = kw.get('came_from', '/')
        return dict(now=now, page='login', header=lambda *arg: None,
                    footer=lambda *arg: None, came_from=came_from)

The important code to look at here is the @authorize.require decorator, which 
checks that the currently logged in user is logged in user is 'editor'.  

Controller-level authorization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@TODO


Predicates
~~~~~~~~~~

@TODO: Elaborate more on them (more importantly, explain what they are first).

There authorize module contains various predicate checker functions:

 * is_user  -- checks to see that the logged in user IS the specified user
 * in_group  -- checks to see that the logged in user is in the specified group
 * in_all_groups  -- is the user is all the groups specified
 * in_any_group -- is the user in any of these groups
 * not_anonymous -- any logged in user will do
 * has_permission -- logged in user has the specified permission
 * has_all_permissions -- has all the permissions listed
 * has_any_permission -- has any of the listed permissions

There are also a couple of predicates you can use to aggregate the above 
permissions. 

 * All -- used to combine the above predicate checks requiring that all of them 
   are true. 
 * Any -- same as All, but only requires that one of the checks return true. 

If a user is not logged in or does not have the proper permissions the 
predicate checks throw a 403 (HTTP Not Authorized) which is caught by the 
tg.ext.repoze.who middleware which displays the login page allowing the user
to login, and redirecting the user back to the proper page when they are done.


Plugins
-------

@TODO: Most probably Gustavo's job because this is the most important change
from tg.ext.repoze.who.

Groups handling plugins
~~~~~~~~~~~~~~~~~~~~~~~
@TODO: Most probably Gustavo's job.

Permissions handling plugins
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@TODO: Most probably Gustavo's job.


Advanced topics
---------------

.. toctree::
    :maxdepth: 2

    ManagingSources
    WritingSourceAdapters
