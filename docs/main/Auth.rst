tg.ext.repoze.who is a plugable system for authorization/authentication based
on sqlalchemy, which is backwards compatible with the TG1 Identity auth system.

It's based on repoze.who which is designed just for authentication (thus the 
who monicker). The basic design is that the user's name, groups and 
permissions are looked up on the way in, and added to the request on the way 
in to TurboGears.  tg.ext.repoze.who also provides some decorators that 
check permissions for you, which have the same API as the Turbogears one 
identity module. 

To use this just answer `yes` during the `paster quickstart` process when it
asks you if you want auth::

  Do you need Identity (usernames/passwords) in this project? [no] yes

You'll then get a new file with authorization code added for you. 

You can then write code like this to require authorization::

   from tgrepozewho import authorize

 - Add the following methods to your controllers.root:RootController
   class::

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

There authorize module contains various predicate checker functions: 


* is_user  -- checks to see that the logged in user IS the specified user
* in_group  -- checks to see that the logged in user is in the specified group
* in_all_groups  -- is the user is all the groups specified
* in_any_group -- is the user in any of these groups
* not_anonymous -- any logged in user will do
* has_permission -- logged in user has the specified permission
* has_all_permissions -- has all the permissions listed
* has_any_permission -- has any of the listed permissions

There are also a couple of predicates you can use to aggregate the above permissions. 

* All -- used to combine the above predicate checks requiring that all of them are true. 
* Any -- same as All, but only requires that one of the checks return true. 

If a user is not logged in or does not have the proper permissions the 
predicate checks throw a 403 (HTTP Not Authorized) which is caught by the 
tg.ext.repoze.who middleware which displays the login page allowing the user
to login, and redirecting the user back to the proper page when they are done. 

