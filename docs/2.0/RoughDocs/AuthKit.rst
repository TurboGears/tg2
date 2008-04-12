Warning database storage does not currently work with SQLAlchemy 0.4

= middleware.py =
Add

 . import authkit.authenticate
at the start and

 . app = authkit.authenticate.middleware(app, app_conf)
before

 . app = ErrorDocuments(app, global_conf, mapper=error_mapper, **app_conf)
= development.ini =
Within the [app:main] section add

 . authkit.setup.method = form, cookie
and modify and add

 . authkit.form.authenticate.user.data = visitor:password authkit.cookie.secret = words
= root.py =
Add

 . from authkit.authorize.pylons_adaptors import authorize
 from authkit.permissions import RemoteUser, ValidAuthKitUser
to the imports

For each restricted method add

 . @authorize(ValidAuthKitUser())
to any pages you want protecting. Position in the decorator chain does not seem to be relevant but the method signature needs to be

 . def index(self, *a, **kw):
to avoid AuthKit passing to much into the method. You may need to update ValidAuthKitUser() to whatever access restriction you want for the page.

= nested controllers =
For nested controllers, the authorize decorator doesn't seem to work. At the moment a slightly modified version helps:

def authorize(permission):

 . """ This is a decorator which can be used to decorate a Pylons
 . controller action.
  . It takes the permission to check as the only argument and can be
 used with
  . all types of permission objects. """ def validate(func, self, *args, **kwargs):
   . def app(environ, start_response):
    . return func(self, *args, **kwargs)
   return permission.check(app, request.environ,
    . request.environ["pylons.controller"].start_response)
  return decorator(validate)
= Permissions =
There are at least two kinds of exceptions raised, if permissions fail (depending on the permission:

NotAuthenticatedError and NotAuthorizedError.

The second sort seems to lead to 404 Error documents, which can be very confusing.

Setting the error to NotAuthenticatedError for this kind of permission, leads to behaviour very similar to turbogears.identity: displaying a login form.

For Example:

HasAuthKitRole('admin',error=NotAuthenticatedError)
