"""Configuration Helpers for TurboGears 2"""
import atexit
import os
import logging
from copy import copy
import mimetypes
from UserDict import DictMixin

from pylons.i18n import ugettext
from genshi.filters import Translator

from pylons import config as pylons_config
from beaker.middleware import SessionMiddleware, CacheMiddleware
from paste.cascade import Cascade
from paste.registry import RegistryManager
from paste.urlparser import StaticURLParser
from paste.deploy.converters import asbool
from pylons.middleware import report_libs, StatusCodeRedirect

import tg
from tg import TGApp
from tg.error import ErrorHandler
from tg.util import Bunch, get_partial_dict, DottedFileNameFinder

from routes import Mapper
from routes.middleware import RoutesMiddleware
from webob import Request

from tw.api import make_middleware as tw_middleware

log = logging.getLogger(__name__)

class ConfigurationError(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message):
        self.message = message

class PylonsConfigWrapper(DictMixin):
    """Wrapper for the Pylons configuration.

    Simple wrapper for the Pylons config object that provides attribute
    style access to the Pylons config dictionary.

    When used in TG, items with keys like "pylons.response_options" will
    be available via config.pylons.response_options as well as
    config['pylons.response_options'].

    This class works by proxying all attribute and dictionary access to
    the underlying Pylons config object, which is an application local
    proxy that allows for multiple Pylons/TG2 applicatoins to live
    in the same process simultaneously, but to always get the right
    config data for the application that's requesting them.

    Sites, with seeking to maximize needs may prefer to use the Pylons
    config stacked object proxy directly, using just dictionary style
    access, particularly whenever config is checked on a per-request basis.

    """

    def __init__(self, dict_to_wrap):
        """Initialize the object by passing in pylons config to be wrapped"""
        self.__dict__['config_proxy'] = dict_to_wrap

    def __getitem__(self, key):
        return  self.config_proxy.current_conf()[key]

    def __setitem__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __getattr__(self, key):
        """Our custom attribute getter.

        Tries to get the attribute off the wrapped object first,
        if that does not work, tries dictionary lookup, and finally
        tries to grab all keys that start with the attribute and
        return sub-dictionaries that can be looked up.

        """
        try:
            return self.config_proxy.__getattribute__(key)
        except AttributeError:
            try:
                return self.config_proxy.current_conf()[key]
            except KeyError:
                return get_partial_dict(key, self.config_proxy.current_conf())

    def __setattr__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __delattr__(self, name):
        try:
            del self.config_proxy.current_conf()[name]
        except KeyError:
            raise AttributeError(name)

    def keys(self):
        return self.config_proxy.keys()


#Create a config object that has attribute style lookup built in.
config = PylonsConfigWrapper(pylons_config)


class AppConfig(Bunch):
    """Class to store application configuration.

    This class should have configuration/setup information
    that is *necessary* for proper application function.
    Deployment specific configuration information should go in
    the config files (e.g. development.ini or deployment.ini).

    AppConfig instances have a number of methods that are meant to be
    overridden by users who wish to have finer grained control over
    the setup of the WSGI envirnment in which their application is run.

    This is the place to configure custom routes, transaction handling,
    error handling, etc.

    """

    def __init__(self):
        """Creates some configuration defaults"""

        # Create a few bunches we know we'll use
        self.paths = Bunch()
        self.render_functions = Bunch()
        # And also very often...
        self.sa_auth = Bunch()
        self.sa_auth.translations = Bunch()

        #Set individual defaults
        self.auto_reload_templates = True
        self.auth_backend = None
        self.default_renderer = 'genshi'
        self.serve_static = True
        self.stand_alone = True

        # this is to activate the legacy renderers
        # legacy renderers are buffet interface plugins
        self.use_legacy_renderer = False
        # if this is set to True the @expose decorator will be able to
        # specify template names using a dotted name that will be searched
        # in the python path. This option is used in tg.render.render_genshi
        # TODO: we should set this to False once we implement simple names
        # support in the @expose decorator as explained in #1942
        # for the moment only the dotted names notation is supported with the
        # new generation renderer functions
        self.use_dotted_templatenames = True

        self.use_toscawidgets = True
        self.use_transaction_manager = True

        #Registy for functions to be called on startup/teardown
        self.call_on_startup = []
        self.call_on_shutdown = []
        # The codes TG should display an error page for. All other HTTP errors are
        # sent to the client or left for some middleware above us to handle
        self.handle_status_codes = [403, 404]

    def setup_startup_and_shutdown(self):
        for cmd in self.call_on_startup:
            if callable(cmd):
                try:
                    cmd()
                except Exception, error:
                    log.debug("Error registering %s at startup: %s" % (cmd, error ))
            else:
                log.debug("Unable to register %s for startup" % cmd )

        for cmd in self.call_on_shutdown:
            if callable(cmd):
                atexit.register(cmd)
            else:
                log.debug("Unable to register %s for shutdown" % cmd )

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
        access, so it's automatically setup when we create the pylons config.

        Besides basic initialization, this method copies all the values
        in base_config into the ``pylons.config`` and ``tg.config`` objects.

        """
        pylons_config.init_app(global_conf, app_conf,
                        package=self.package.__name__,
                        paths=self.paths)
        config.update(self)

    def setup_routes(self):
        """Setup the default TG2 routes

        Overide this and setup your own routes maps if you want to use
        custom routes.

        """

        map = Mapper(directory=config['pylons.paths']['controllers'],
                    always_scan=config['debug'])

        # Setup a default route for the root of object dispatch
        map.connect('*url', controller='root', action='routes_placeholder')

        config['routes.map'] = map

    def setup_helpers_and_globals(self):
        """Add helpers and globals objects to the config.

        Override this method to customize the way that ``app_globals``
        and ``helpers`` are setup.

        """

        config['pylons.app_globals'] = self.package.lib.app_globals.Globals()
        g = config['pylons.app_globals']
        g.dotted_filename_finder = DottedFileNameFinder()
        config['pylons.helpers'] = self.package.lib.helpers
        config['pylons.h'] = self.package.lib.helpers

    def setup_sa_auth_backend(self):
        """This method adds sa_auth information to the config."""
        defaults = {
                    'form_plugin': None
                   }
        # The developer must have defined a 'sa_auth' section, because
        # values such as the User, Group or Permission classes must be
        # explicitly defined.
        config['sa_auth'] = defaults
        config['sa_auth'].update(self.sa_auth)

    def setup_mako_renderer(self):
        """Setup a renderer and loader for mako templates.

        Override this to customize the way that the mako template
        renderer is setup.  In particular if you want to setup
        a different set of search paths, different encodings, or
        additonal imports, all you need to do is update the
        ``TemplateLookup`` constructor.

        You can also use your own render_mako function instead of the one
        provided by tg.render.

        """
        from tg.dottednamesupport import DottedTemplateLookup
        from mako.lookup import TemplateLookup

        from tg.render import render_mako


        if config.get('use_dotted_templatenames', False):
            # Support dotted names by injecting a slightly different template
            # lookup system that will return templates from dotted template
            # notation.
            config['pylons.app_globals'].mako_lookup = DottedTemplateLookup(
                input_encoding='utf-8', output_encoding='utf-8',
                imports=['from webhelpers.html import escape'],
                default_filters=['escape'])

        else:
            compiled_dir = tg.config.get('templating.mako.compiled_templates_dir', None)

            if not compiled_dir:
                # no specific compile dir give by conf... we expect that
                # the server will have access to the first template dir
                # to write the compiled version...
                # If this is not the case we are doomed and the user should
                # provide us the required config...
                compiled_dir = self.paths['templates'][0]

            # If no dotted names support was required we will just setup
            # a file system based template lookup mechanism.
            compiled_dir = tg.config.get('templating.mako.compiled_templates_dir', None)

            if not compiled_dir:
                # no specific compile dir give by conf... we expect that
                # the server will have access to the first template dir
                # to write the compiled version...
                # If this is not the case we are doomed and the user should
                # provide us the required config...
                compiled_dir = self.paths['templates'][0]

            config['pylons.app_globals'].mako_lookup = TemplateLookup(
                directories=self.paths['templates'],
                module_directory=compiled_dir,
                input_encoding='utf-8', output_encoding='utf-8',
                imports=['from webhelpers.html import escape'],
                default_filters=['escape'],
                filesystem_checks=self.auto_reload_templates)

        self.render_functions.mako = render_mako

    def setup_chameleongenshi_renderer(self):
        """Setup a renderer and loader for the chameleon.genshi engine."""
        from chameleon.genshi.loader import TemplateLoader as ChameleonLoader
        from tg.render import render_chameleon_genshi

        loader = ChameleonLoader(search_path=self.paths.templates,
                                auto_reload=self.auto_reload_templates)

        config['pylons.app_globals'].chameleon_genshi_loader = loader

        self.render_functions.chameleon_genshi = render_chameleon_genshi

    def setup_genshi_renderer(self):
        """Setup a renderer and loader for Genshi templates.

        Override this to customize the way that the internationalization
        filter, template loader

        """
        from genshi.template import TemplateLoader
        from tg.render import render_genshi

        def template_loaded(template):
            """Plug-in our i18n function to Genshi, once the template is loaded.

            This function will be called by genshi TemplateLoader after
            loading the template.

            """
            template.filters.insert(0, Translator(ugettext))

        loader = TemplateLoader(search_path=self.paths.templates,
                                auto_reload=self.auto_reload_templates,
                                callback=template_loaded)

        config['pylons.app_globals'].genshi_loader = loader

        self.render_functions.genshi = render_genshi

    def setup_jinja_renderer(self):
        """Setup a renderer and loader for Jinja2 templates."""
        from jinja2 import ChoiceLoader, Environment, FileSystemLoader
        from tg.render import render_jinja

        config['pylons.app_globals'].jinja2_env = Environment(loader=ChoiceLoader(
                [FileSystemLoader(path) for path in self.paths['templates']]),
                auto_reload=self.auto_reload_templates)

        # Jinja's unable to request c's attributes without strict_c
        config['pylons.strict_c'] = True

        self.render_functions.jinja = render_jinja


    def setup_default_renderer(self):
        """Setup template defaults in the buffed plugin.

        This is only used when use_legacy_renderer is set to True
        and it will not get deprecated in the next major TurboGears release.

        """
        #T his is specific to buffet, will not be needed later
        config['buffet.template_engines'].pop()
        template_location = '%s.templates' % self.package.__name__
        template_location = '%s.templates' % self.package.__name__

        def template_loaded(template):
            template.filters.insert(0, Translator(ugettext))

        # Set some default options for genshi
        options = {
            'genshi.loader_callback': template_loaded,
            'genshi.default_format': 'xhtml',
        }

        # Override those options from config
        config['buffet.template_options'].update(options)
        config.add_template_engine(self.default_renderer,
                                   template_location,  {})

    def setup_mimetypes(self):
        lookup = {'.json':'application/json'}
        lookup.update(config.get('mimetype_lookup', {}))

        for key, value in lookup.iteritems():
            mimetypes.add_type(value, key)

    def setup_sqlalchemy(self):
        """Setup SQLAlchemy database engine."""
        from sqlalchemy import engine_from_config
        engine = engine_from_config(pylons_config, 'sqlalchemy.')
        config['pylons.app_globals'].sa_engine = engine
        # Pass the engine to initmodel, to be able to introspect tables
        self.package.model.init_model(engine)

    def make_load_environment(self):
        """Return a load_environment function.

        The returned load_environment function can be called to configure
        the TurboGears runtime environment for this particular application.
        You can do this dynamically with multiple nested TG applications
        if necessary.

        """

        def load_environment(global_conf, app_conf):
            """Configure the Pylons environment via ``pylons.config``."""
            global_conf=Bunch(global_conf)
            app_conf=Bunch(app_conf)
            #Regesters functions to be called at startup and shutdown
            #from self.call_on_startup and shutdown respectively.
            self.setup_startup_and_shutdown()

            self.setup_paths()
            self.init_config(global_conf, app_conf)
            self.setup_routes()
            self.setup_helpers_and_globals()
            self.setup_mimetypes()

            if self.auth_backend == "sqlalchemy":
                self.setup_sa_auth_backend()

            if 'genshi' in self.renderers:
                self.setup_genshi_renderer()

            if 'chameleon_genshi' in self.renderers:
                self.setup_chameleongenshi_renderer()

            if 'mako' in self.renderers:
                self.setup_mako_renderer()

            if 'jinja' in self.renderers:
                self.setup_jinja_renderer()

            if self.use_legacy_renderer:
                self.setup_default_renderer()

            if self.use_sqlalchemy:
                self.setup_sqlalchemy()

        return load_environment


    def add_error_middleware(self, global_conf, app):
        """Add middleware which handles errors and exceptions."""
        app = ErrorHandler(app, global_conf, **config['pylons.errorware'])

        # Display error documents for self.handle_status_codes status codes (and
        # 500 when debug is disabled)

        if asbool(config['debug']):
            app = StatusCodeRedirect(app, self.handle_status_codes)
        else:
            app = StatusCodeRedirect(app, self.handle_status_codes + [500])
        return app

    def add_auth_middleware(self, app, skip_authentication):
        """
        Configure authentication and authorization.
        
        :param app: The TG2 application.
        :param skip_authentication: Should authentication be skipped if
            explicitly requested? (used by repoze.who-testutil)
        :type skip_authentication: bool
        
        """
        from repoze.what.plugins.quickstart import setup_sql_auth
        from repoze.what.plugins.pylonshq import booleanize_predicates
        
        # Predicates booleanized:
        booleanize_predicates()

        # Configuring auth logging:
        if 'log_stream' not in self.sa_auth:
            self.sa_auth['log_stream'] = logging.getLogger('auth')

        # Removing keywords not used by repoze.who:
        auth_args = copy(self.sa_auth)
        if 'password_encryption_method' in auth_args:
            del auth_args['password_encryption_method']
        if not skip_authentication:
            if not 'cookie_secret' in auth_args.keys():
                msg = "base_config.sa_auth.cookie_secret is required " \
                "you must define it in app_cfg.py or set " \
                "sa_auth.cookie_secret in development.ini"
                print msg
                raise ConfigurationError(message=msg)
        app = setup_sql_auth(app, skip_authentication=skip_authentication,
                             **auth_args)
        return app

    def add_core_middleware(self, app):
        """Add support for routes dispatch, sessions, and caching."""
        app = RoutesMiddleware(app, config['routes.map'])
        app = SessionMiddleware(app, config)
        app = CacheMiddleware(app, config)
        return app

    def add_tosca_middleware(self, app):
        """Configure the ToscaWidgets middleware."""
        app = tw_middleware(app, {
            'toscawidgets.framework.default_view': self.default_renderer,
            'toscawidgets.framework.translator': ugettext,
            'toscawidgets.middleware.inject_resources': True,
            })
        return app

    def add_static_file_middleware(self, app):
        static_app = StaticURLParser(config['pylons.paths']['static_files'])
        app = Cascade([static_app, app])
        return app

    def commit_veto(self, environ, status, headers):
        """Veto a commit.

        This hook is called by repoze.tm in case we want to veto a commit
        for some reason. Return True to force a rollback.

        By default we veto if the response's status code is an error code.
        Override this method, or monkey patch the instancemethod, to fine
        tune this behaviour.

        """
        return not 200 <= int(status.split(None, 1)[0]) < 400

    def add_tm_middleware(self, app):
        """Set up the transaction managment middleware.

        To abort a transaction inside a TG2 app::

          import transaction
          transaction.doom()

        By default http error responses also roll back transactions, but this
        behavior can be overridden by overriding base_config.commit_veto.

        """
        from repoze.tm import make_tm
        return make_tm(app, self.commit_veto)

    def add_dbsession_remover_middleware(self, app):
        """Set up middleware that cleans up the sqlalchemy session.

        The default behavior of TG 2 is to clean up the session on every
        request.  Only override this method if you know what you are doing!

        """
        def remover(environ, start_response):
            try:
                return app(environ, start_response)
            finally:
                log.debug("Removing DBSession from current thread")
                self.DBSession.remove()
        return remover

    def setup_tg_wsgi_app(self, load_environment):
        """Create a base TG app, with all the standard middleware.

        ``load_environment``
            A required callable, which sets up the basic evironment
            needed for the application.
        ``setup_vars``
            A dictionary with all special values necessary for setting up
            the base wsgi app.

        """

        def make_base_app(global_conf, wrap_app=None, full_stack=True, **app_conf):
            """Create a tg WSGI application and return it.

            ``wrap_app``
                a WSGI middleware component which takes the core turbogears
                application and wraps it -- inside all the WSGI-components
                provided by TG and Pylons. This allows you to work with the
                full environment that your TG application would get before
                anything happens in the application itself.

            ``global_conf``
                The inherited configuration for this application. Normally
                from the [DEFAULT] section of the Paste ini file.

            ``full_stack``
                Whether or not this application provides a full WSGI stack (by
                default, meaning it handles its own exceptions and errors).
                Disable full_stack when this application is "managed" by
                another WSGI middleware.

            ``app_conf``
                The application's local configuration. Normally specified in
                the [app:<name>] section of the Paste ini file (where <name>
                defaults to main).

            """
            # Configure the Pylons environment
            load_environment(global_conf, app_conf)
            app = TGApp()
            if wrap_app:
                app = wrap_app(app)
            app = self.add_core_middleware(app)

            if self.use_toscawidgets:
                app = self.add_tosca_middleware(app)

            if self.auth_backend == "sqlalchemy":
                # Skipping authentication if explicitly requested. Used by 
                # repoze.who-testutil:
                skip_authentication = app_conf.get('skip_authentication', False)
                app = self.add_auth_middleware(app, skip_authentication)

            if self.use_transaction_manager:
                app = self.add_tm_middleware(app)

            if self.use_sqlalchemy:
                if not hasattr(self, 'DBSession'):
                    # If the user hasn't specified a scoped_session, assume
                    # he/she uses the default DBSession in model
                    self.DBSession = self.model.DBSession
                app = self.add_dbsession_remover_middleware(app)

            app = maybe_make_body_seekable(app)


            if asbool(full_stack):
                if (self.auth_backend is None
                        and 401 not in self.handle_status_codes):
                    # If there's no auth backend configured which traps 401
                    # responses we redirect those responses to a nicely
                    # formatted error page
                    self.handle_status_codes.append(401)
                # This should nevery be true for internal nested apps
                app = self.add_error_middleware(global_conf, app)

            # Establish the registry for this application
            app = RegistryManager(app)

            # Static files (if running in production, and Apache or another
            # web server is serving static files)
            if self.serve_static:
                app = self.add_static_file_middleware(app)

            return app

        return make_base_app

def maybe_make_body_seekable(app):
    def wrapper(environ, start_response):
        if pylons_config.get('make_body_seekable'):
            log.debug("Making request body seekable")
            Request(environ).make_body_seekable()
        return app(environ, start_response)
    return wrapper
