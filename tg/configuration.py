"""Simple AppSetup helper class"""
import os
import logging
from pylons.i18n import ugettext
from genshi.filters import Translator

from pylons import config as pylons_config
from beaker.middleware import SessionMiddleware, CacheMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons.middleware import ErrorHandler, StatusCodeRedirect
from tg import TGApp
from tg.util import Bunch, get_partial_dict
from routes import Mapper
from routes.middleware import RoutesMiddleware

from tw.api import make_middleware as tw_middleware

log = logging.getLogger(__name__)


class PylonsConfigWrapper(dict):
    """Simple wrapper for the pylons config object that provides attribute 
    style access to the pylons config dictionary.

    When used in TG, items with keys like "pylons.response_options" will 
    be available via config.pylons.response_options as well as 
    config['pylons.response_options'].

    This class works by proxying all attribute and dictionary access to
    the underlying pylons config object, which is a application local 
    proxy that allows for multiple pylons/tg2 applicatoins to live
    in the same process simultaniously, but to always get the right 
    config data for the app that's requesting them. 
    """

    def __init__(self, dict_to_wrap):
        """Initialize by passing in a dictionary to be wrapped"""
        self.__dict__['config_proxy'] = dict_to_wrap

    def __getitem__(self, key):
        return  self.config_proxy.current_conf()[key]

    def __setitem__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __getattr__(self, key):
        """Tries to get the attribute off the wrapped object first, 
        if that does not work, tries dictionary lookup, and finally
        tries to grab all keys that start with the attribute and
        return sub-dictionary, that can be looked up. """
        try: 
            return self.config_proxy.__getattribute__(key)
        except AttributeError:
            try:
                return self.config_proxy.current_conf()[key]
            except KeyError:
                get_partial_dict(key, self.config_proxy.current_conf())

    def __setattr__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __delattr__(self, name):
           try:
               del self.config_proxy.current_conf()[name]
           except KeyError:
               raise AttributeError(name)

    def update(self, new_dict):
        self.config_proxy.current_conf().update(new_dict)

    def __str__(self):
        return self.config_proxy.__str__()

    @property
    def pylons(self):
        return get_partial_dict('pylons', self.config_proxy.current_conf())


#Create a config object that has attribute style lookup built in. 
config = PylonsConfigWrapper(pylons_config)


class AppConfig(Bunch):
    """Class to store application configuration
    
    This class should have configuration/setup information 
    that is NECESSARY for proper application function.  
    Deployment specific configuration information should go in 
    the config files (eg: dvelopment.ini or production.ini)
    
    AppConfig instances have a number of methods that are meant to be 
    overridden by users who wish to have finer grained controll over 
    the setup of the WSGI envirnment in which their applcation is run. 
    
    This is the place to configure custom routes, transaction handling, 
    error handling, etc. 
    """
    
    def __init__(self):
        """Creates some configuration defaults"""
        
        #Create a few bunches we know we'll use
        self.paths = Bunch()
        self.render_functions = Bunch()
        
        #Set individual defaults
        self.stand_alone = True
        self.default_renderer = 'genshi'
        self.auth_backend = None
        self.serve_static = True
        self.use_legacy_render = True

    
    def setup_paths(self):
        root = os.path.dirname(os.path.abspath(self.package.__file__))
        # The default paths:
        paths = Bunch(root=root,
                     controllers=os.path.join(root, 'controllers'),
                     static_files=os.path.join(root, 'public'),
                     templates=[os.path.join(root, 'templates')])
        # If the user defined custom paths, then use them instead of the
        # default ones:
        paths.update(self.paths)
        self.paths = paths

    def init_config(self, global_conf, app_conf):
        """Initialize the config object.
        
        tg.config is a proxy for pylons.config that allows attribute style
        access, so it's automatically setup when we create the poylons config
        
        Besides basic initialization,  this method copies all the values 
        in base_config  into the ``tg.config`` object. 
        """
        pylons_config.init_app(global_conf, app_conf, 
                        package=self.package.__name__,
                        paths=self.paths)
        config.update(self)
                        
    def setup_routes(self):
        """Setup the default TG2 routes
        
        Overide this and setup your own routes maps if you want to use routes.
        """
        map = Mapper(directory=config['pylons.paths']['controllers'],
                    always_scan=config['debug'])

        # Setup a default route for the error controller:
        map.connect('error/:action/:id', controller='error')
        # Setup a default route for the root of object dispatch
        map.connect('*url', controller='root', action='routes_placeholder')
        
        config['routes.map'] = map
    
    def setup_helpers_and_globals(self):
        config['pylons.app_globals'] = self.package.lib.app_globals.Globals()
        config['pylons.h'] = self.package.lib.helpers
    
    def setup_sa_auth_backend(self):
        defaults = {'users_table':'tg_user',
                    'groups_table':'tg_group',
                    'permissions_table':'tg_permission',
                    'password_encryption_method':'sha1',
                    'form_plugin': None
                   }
        # The developer must have defined a 'sa_auth' section, because
        # values such as the User, Group or Permission classes must be
        # explicitly defined.
        config['sa_auth'] = defaults.update(config['sa_auth'])
    
    def setup_mako_renderer(self):
        """Setup a renderer and loader for mako templates"""
        from mako.lookup import TemplateLookup
        from tg.render import render_mako

        config['pylons.app_globals'].mako_lookup = TemplateLookup(
            directories=self.paths['templates'],
            module_directory=self.paths['templates'],
            input_encoding='utf-8', output_encoding='utf-8',
            imports=['from webhelpers.html import escape'],
            default_filters=['escape'])
        
        self.renderer_functions.mako = render_mako
        
    def setup_genshi_renderer(self):
        """Setup a renderer and loader for Genshi templates"""
        from genshi.template import TemplateLoader
        from tg.render import render_genshi

        def template_loaded(template):
            "Plug-in our i18n function to Genshi."
            genshi.template.filters.insert(0, Translator(ugettext))
        loader = TemplateLoader(search_path=self.paths.templates, 
                                auto_reload=True)
                                
        config['pylons.app_globals'].genshi_loader = loader

        self.render_functions.genshi = render_genshi
    
    def setup_jinja_renderer(self):
        """Setup a renderer and loader for Jinja templates"""
        from jinja import ChoiceLoader, Environment, FileSystemLoader
        from tg.render import render_jinja

        config['pylons.app_globals'].jinja_env = Environment(loader=ChoiceLoader(
                [FileSystemLoader(path) for path in self.paths['templates']]))
        # Jinja's unable to request c's attributes without strict_c
        config['pylons.strict_c'] = True

        self.renderer_functions.jinja = render_jinja
    
    def setup_default_renderer(self):
        """Setup template defaults in the buffed plugin
        
        This is only used when use_legacy_renderer is set to True
        
        And it will not depricated in the next major turbogears 
        release.
        """
        #This is specific to buffet, will not be needed later
        config['buffet.template_engines'].pop()
        template_location = '%s.templates' %self.package.__name__
        config.add_template_engine(self.default_renderer, 
                                   template_location,  {})
    
    def setup_sqlalchemy(self):
        """Setup SQLAlchemy database engine"""
        from sqlalchemy import engine_from_config
        engine = engine_from_config(pylons_config, 'sqlalchemy.')
        config['pylons.app_globals'].sa_engine = engine
        # Pass the engine to initmodel, to be able to introspect tables
        self.package.model.init_model(engine)
        
    def make_load_environment(self):
        """Returns a load_environment function 
        
        The returned load_environment function can be called to configure the 
        TurboGears runtime environment for this particular application.  You 
        can do this dynamically with multiple nested TG applications if 
        nessisary."""
        
        def load_environment(global_conf, app_conf):
            """Configure the Pylons environment via the ``pylons.config``
            object
            """
            global_conf=Bunch(global_conf)
            app_conf=Bunch(app_conf)
            self.setup_paths()
            self.init_config(global_conf, app_conf)
            self.setup_routes()
            self.setup_helpers_and_globals()
            
            if self.auth_backend == "sqlalchemy": 
                self.setup_sa_auth_backend()

            if 'genshi' in self.renderers: 
                self.setup_genshi_renderer()

            if 'mako' in self.renderers:
                self.setup_mako_renderer()
            
            if 'jinja' in self.renderers:
                self.setup_jinja_renderer()

            self.setup_default_renderer()
            
            if self.use_sqlalchemy:
                self.setup_sqlalchemy()

        return load_environment


    def add_error_middleware(self, global_conf, app):
        """Adds middleware which handles errors and exceptions"""
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for 401, 403, 404 status codes (and
        # 500 when debug is disabled)
        if asbool(config['debug']):
            app = StatusCodeRedirect(app)
        else:
            app = StatusCodeRedirect(app, [400, 401, 403, 404, 500])
        return app

    def add_auth_middleware(self, app):
        """Configure authorization/authentication"""
        from tg.ext.repoze.who.middleware import make_who_middleware

        auth = self.sa_auth

        app = make_who_middleware(app, config, auth.user_class, 
                                  auth.user_criterion, 
                                  auth.user_id_column, 
                                  auth.dbsession,
                                  )
        return app
    
    def add_core_middleware(self, app):    
        """Adds support for routes dispatch, sessions, and caching"""
        app = RoutesMiddleware(app, config['routes.map'])
        app = SessionMiddleware(app, config)
        app = CacheMiddleware(app, config)
        return app
    
    def add_tosca_middleware(self, app):
        """Configure the ToscaWidgets middleware"""
        app = tw_middleware(app, {
            'toscawidgets.framework.default_view': 
            self.default_renderer,
            'toscawidgets.middleware.inject_resources': True,
            })
        return app
    
    def add_static_file_middleware(self, app):
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, app])
        return app

    def commit_veto(self, environ, status, headers):
        """
        This hook is called by repoze.tm in case we want to veto a commit
        for some reason. Return True to force a rollback.

        By default we veto if the response's status code is an error code.
        Override this method, or monkey patch the instancemethod, to fine
        tune this behaviour.
        """
        return not (200 <= int(status.split()[0]) < 400)

    def add_tm_middleware(self, app):
        """Sets up the transaction managment middleware
        
        To abort a transaction inside a TG2 app::
        
          import transaction
          transaction.doom()
        
        By default http error responses also roll back transactions, 
        but this behavior can be overridden by overiding 
        base_config.commit_veto
        """
        from repoze.tm import make_tm
        return make_tm(app, self.commit_veto)

    def add_dbsession_remover_middleware(self, app):
        """Sets up middleware that cleans up the sqlalchmy session
        
        The default behavior of TG2 is to clean up the session on 
        every request.  Only overide this method if you know what you
        are doing!
        
        """
        def remover(environ, start_response):
            try:
                return app(environ, start_response)
            finally:
                log.debug("Removing DBSession from current thread")
                self.DBSession.remove()
        return remover

    def setup_tg_wsgi_app(self, load_environment):
        """Create a base TG app, with all the standard middleware

        ``load_environment``
            A required callable, which sets up the basic application
            evironment.
        ``setup_vars``
            A dictionary any special values nessisary for setting up
            the base wsgi app.
        """                  

        def make_base_app(global_conf, wrap_app=None, full_stack=True, **app_conf):
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
            app = TGApp()
            if wrap_app: 
                wrap_app(app)
            app = self.add_core_middleware(app)
            app = self.add_tosca_middleware(app)

            if self.auth_backend == "sqlalchemy":
                app = self.add_auth_middleware(app)

            app = self.add_tm_middleware(app)
            if self.use_sqlalchemy:
                if not hasattr(self, 'DBSession'):
                    # If the user hasn't specified a scoped_session, assume
                    # he/she uses the default DBSession in model
                    self.DBSession = self.model.DBSession
                app = self.add_dbsession_remover_middleware(app)

            if asbool(full_stack):
                # This should nevery be true for internal nested apps
                app = self.add_error_middleware(global_conf, app)

            # Establish the Registry for this application
            app = RegistryManager(app)

            # Static files (If running in production, and Apache or another 
            # web server is serving static files) 
            if self.serve_static: 
                app = self.add_static_file_middleware(app)
            return app

        return make_base_app
