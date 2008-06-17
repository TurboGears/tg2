"""tg middleware initialization"""
from beaker.middleware import SessionMiddleware, CacheMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons import config
from pylons.middleware import ErrorHandler, StaticJavascripts, \
    StatusCodeRedirect
from pylons.wsgiapp import PylonsApp
from routes.middleware import RoutesMiddleware

from tw.api import make_middleware as tw_middleware

def setup_tg_wsgi_app(load_environment, base_config):
    """Create a base TG app, with all the standard middleware
    
    ``load_environment``
        A required callable, which sets up the basic application
        evironment.
    ``setup_vars``
        A dictionary any special values nessisary for setting up
        the base wsgi app.
    """                  
    
    def make_base_app(global_conf, full_stack=True, **app_conf):
        """Create a tg WSGI application and return it

        ``global_conf``
            The inherited configuration for this application. Normally from
            the [DEFAULT] section of the Paste ini file.

        ``full_stack``
            Whether or not this application provides a full WSGI stack (by
            default, meaning it handles its own exceptions and errors).
            Disable full_stack when this application is "managed" by
            another WSGI middleware.

        ``app_conf``
            The application's local configuration. Normally specified in the
            [app:<name>] section of the Paste ini file (where <name>
            defaults to main).
        """
        # Configure the Pylons environment
        load_environment(global_conf, app_conf)

        # The Pylons WSGI app
        app = PylonsApp()

        # Routing/Session/Cache Middleware
        app = RoutesMiddleware(app, config['routes.map'])
        app = SessionMiddleware(app, config)
        app = CacheMiddleware(app, config)

        # ToscaWidgets Middleware
        app = tw_middleware(app, {
            'toscawidgets.framework.default_view': 
            base_config.default_renderer
            })

        if base_config.auth_backend == "sqlalchemy":
            # configure identity Middleware
            from tg.ext.repoze.who.middleware import make_who_middleware
            
            auth = base_config.sa_auth
            
            app = make_who_middleware(app, config, auth.User, 
                                      auth.user_criterion, auth.user_id_col, 
                                      auth.DBSession)

        if asbool(full_stack):
            # Handle Python exceptions
            app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

            # Display error documents for 401, 403, 404 status codes (and
            # 500 when debug is disabled)
            if asbool(config['debug']):
                app = StatusCodeRedirect(app)
            else:
                app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])

        # Establish the Registry for this application
        app = RegistryManager(app)

        # Static files (If running in production, and Apache or another web
        # server is handling this static content, remove the following 3 lines)
        javascripts_app = StaticJavascripts()
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, javascripts_app, app])
        return app
        
    return make_base_app