"""Configuration Helpers for TurboGears 2"""
import atexit
import os
import logging
import warnings
from copy import copy
import mimetypes
from UserDict import DictMixin

from pylons.i18n import ugettext

from pylons.configuration import config as pylons_config
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

log = logging.getLogger(__name__)

class TGConfigError(Exception):pass

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
        self.stand_alone = True

        # this is to activate the legacy renderers
        # legacy renderers are buffet interface plugins
        self.use_legacy_renderer = False

        self.use_toscawidgets = True
        self.use_transaction_manager = True
        self.use_toscawidgets2 = False

        #Registy for functions to be called on startup/teardown
        self.call_on_startup = []
        self.call_on_shutdown = []
        # The codes TG should display an error page for. All other HTTP errors are
        # sent to the client or left for some middleware above us to handle
        self.handle_status_codes = [403, 404]

        #override this variable to customize how the tw2 middleware is set up
        self.custom_tw2_config = {}


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

        tg.config is a proxy for pylons.configuration.config that allows
        attribute style access, so it's automatically setup when we create
        the pylons config.

        Besides basic initialization, this method copies all the values
        in base_config into the ``pylons.configuration.config`` and
        ``tg.config`` objects.

        """
        pylons_config.init_app(global_conf, app_conf,
                        package=self.package.__name__,
                        paths=self.paths)
        config.update(self)
        # set up the response options to None.  This allows
        # you to set the proper content type within a controller method
        # if you choose.
        pylons_config['pylons.response_options']['headers']['Content-Type'] = None

        #see http://trac.turbogears.org/ticket/2247
        if asbool(config['debug']):
            warnings.simplefilter("ignore")
            config['pylons.strict_c'] = True
            warnings.resetwarnings()
            config['pylons.stritmpl_contextt_tmpl_context'] = True
        self.after_init_config()

    def after_init_config(self):
        """
        Override this method to set up configuration variables at the application
        level.  This method will be called after your configuration object has
        been initialized on startup.  Here is how you would use it to override
        the default setting of pylons.stritmpl_contextt_tmpl_context ::

            from tg.configuration import AppConfig
            from pylons import config

            class MyAppConfig(AppConfig):
                def after_init_config(self):
                    config['pylons.stritmpl_contextt_tmpl_context'] = False

            base_config = MyAppConfig()

        """

    def setup_routes(self):
        """Setup the default TG2 routes

        Override this and setup your own routes maps if you want to use
        custom routes.

        It is recommended that you keep the existing application routing in
        tact, and just add new connections to the mapper above the routes_placeholder
        connection.  Lets say you want to add a pylons controller SamplesController,
        inside the controllers/samples.py file of your application.  You would
        augment the app_cfg.py in the following way::

            from routes import Mapper
            from tg.configuration import AppConfig

            class MyAppConfig(AppConfig):
                def setup_routes(self):
                    map = Mapper(directory=config['pylons.paths']['controllers'],
                                always_scan=config['debug'])

                    # Add a Samples route
                    map.connect('/samples/', controller='samples', action=index)

                    # Setup a default route for the root of object dispatch
                    map.connect('*url', controller='root', action='routes_placeholder')

                    config['routes.map'] = map


            base_config = MyAppConfig()

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

    def setup_sa_auth_backend(self):
        """This method adds sa_auth information to the config."""

        if 'beaker.session.secret' not in config:
            raise TGConfigError("You must provide a value for 'beaker.session.secret'  If this is a project quickstarted with TG 2.0.2 or earlier \
double check that you have base_config['beaker.session.secret'] = 'mysecretsecret' in your app_cfg.py file.")

        defaults = {
                    'form_plugin': None,
                    'cookie_secret': config['beaker.session.secret']
                   }

        # The developer must have defined a 'sa_auth' section, because
        # values such as the User, Group or Permission classes must be
        # explicitly defined.
        config['sa_auth'] = defaults
        config['sa_auth'].update(self.sa_auth)

    def setup_mako_renderer(self, use_dotted_templatenames=None):
        """Setup a renderer and loader for mako templates.

        Override this to customize the way that the mako template
        renderer is setup.  In particular if you want to setup
        a different set of search paths, different encodings, or
        additonal imports, all you need to do is update the
        ``TemplateLookup`` constructor.

        You can also use your own render_mako function instead of the one
        provided by tg.render.

        """

        from tg.render import render_mako

        if not use_dotted_templatenames:
            use_dotted_templatenames = asbool(config.get('use_dotted_templatenames', 'true'))


        # If no dotted names support was required we will just setup
        # a file system based template lookup mechanism.
        compiled_dir = tg.config.get('templating.mako.compiled_templates_dir', None)

        if not compiled_dir:
            # Try each given templates path (when are they > 1 ?) for writability..
            for template_path in self.paths['templates']:
                if os.access(template_path, os.W_OK):
                    compiled_dir = template_path
                    break # first match is as good as any

            # Last recourse: project-dir/data/templates (pylons' default directory)
            if not compiled_dir:
                try:
                    root = os.path.dirname(os.path.abspath(self.package.__file__))
                except AttributeError:
                    # Thrown during unit tests when self.package.__file__ doesn't exist
                    root = None

                if root:
                    pylons_default_path = os.path.join(root, '../data/templates')
                    if os.access(pylons_default_path, os.W_OK):
                        compiled_dir = pylons_default_path

                if not compiled_dir:
                    if use_dotted_templatenames:
                        # Gracefully digress to in-memory template caching
                        pass
                    else:
                        raise IOError("None of your templates directory, %s, are "
                            "writable for compiled templates. Please set the "
                            "templating.mako.compiled_templates_dir variable in your "
                            ".ini file" % str(self.paths['templates']))

        if use_dotted_templatenames:
            # Support dotted names by injecting a slightly different template
            # lookup system that will return templates from dotted template notation.
            from tg.dottednames.mako_lookup import DottedTemplateLookup
            config['pylons.app_globals'].mako_lookup = DottedTemplateLookup(
                input_encoding='utf-8', output_encoding='utf-8',
                imports=['from webhelpers.html import escape'],
                module_directory=compiled_dir,
                default_filters=['escape'])

        else:
            from mako.lookup import TemplateLookup
            config['pylons.app_globals'].mako_lookup = TemplateLookup(
                directories=self.paths['templates'],
                module_directory=compiled_dir,
                input_encoding='utf-8', output_encoding='utf-8',
                imports=['from webhelpers.html import escape'],
                default_filters=['escape'],
                filesystem_checks=self.auto_reload_templates)

        self.render_functions.mako = render_mako

    def setup_chameleon_genshi_renderer(self):
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
        from tg.dottednames.genshi_lookup import GenshiTemplateLoader
        from tg.render import render_genshi
        from genshi.filters import Translator

        def template_loaded(template):
            """Plug-in our i18n function to Genshi, once the template is loaded.

            This function will be called by genshi TemplateLoader after
            loading the template.

            """
            template.filters.insert(0, Translator(ugettext))

        if not config.get('use_dotted_templatenames', True):
            from genshi.template import TemplateLoader
            loader = TemplateLoader(search_path=self.paths.templates,
                                    auto_reload=self.auto_reload_templates,
                                    callback=template_loaded)
        else:
            loader = GenshiTemplateLoader(search_path=self.paths.templates,
                                          auto_reload=self.auto_reload_templates,
                                          callback=template_loaded)

        config['pylons.app_globals'].genshi_loader = loader

        self.render_functions.genshi = render_genshi

    def setup_kajiki_renderer(self):
        """Setup a renderer and loader for the fastpt engine."""
        from kajiki.loader import PackageLoader
        from tg.render import render_kajiki
        loader = PackageLoader()
        config['pylons.app_globals'].kajiki_loader = loader
        self.render_functions.kajiki = render_kajiki

    def setup_jinja_renderer(self):
        """Setup a renderer and loader for Jinja2 templates."""
        from jinja2 import ChoiceLoader, Environment, FileSystemLoader
        from tg.render import render_jinja

        config['pylons.app_globals'].jinja2_env = Environment(loader=ChoiceLoader(
                 [FileSystemLoader(path) for path in self.paths['templates']]),
                 auto_reload=self.auto_reload_templates)
        # Jinja's unable to request c's attributes without strict_c
        warnings.simplefilter("ignore")
        config['pylons.strict_c'] = True
        warnings.resetwarnings()
        config['pylons.stritmpl_contextt_tmpl_context'] = True


        self.render_functions.jinja = render_jinja

    def setup_amf_renderer(self):
        from tg.amfify import render_amf
        self.render_functions.amf = render_amf

    def setup_json_renderer(self):
        from tg.render import render_json
        self.render_functions.json = render_json

    def setup_default_renderer(self):
        """Setup template defaults in the buffed plugin.

        This is only used when use_legacy_renderer is set to True
        and it will not get deprecated in the next major TurboGears release.

        """
        #T his is specific to buffet, will not be needed later
        config['buffet.template_engines'].pop()
        template_location = '%s.templates' % self.package.__name__
        template_location = '%s.templates' % self.package.__name__
        from genshi.filters import Translator

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

    def setup_persistence(self):
        """Override this method to define how your application configures it's persistence model.
           the default is to setup sqlalchemy from the cofiguration file, but you might choose
           to set up a persistence system other than sqlalchemy, or add an additional persistence
           layer.  Here is how you would go about setting up a ming (mongo) persistence layer::

            class MingAppConfig(AppConfig):
                def setup_persistence(self):
                    self.ming_ds = DataStore(config['mongo.url'])
                    session = Session.by_name('main')
                    session.bind = self.ming_ds
        """
        if self.use_sqlalchemy:
            self.setup_sqlalchemy()

    def setup_sqlalchemy(self):
        """Setup SQLAlchemy database engine.

        The most common reason for modifying this method is to add
        multiple database support.  To do this you might modify your
        app_cfg.py file in the following manner::

            from tg.configuration import AppConfig, config
            from pylons import config as pylons_config
            from myapp.model import init_model

            # add this before base_config =
            class MultiDBAppConfig(AppConfig):
                def setup_sqlalchemy(self):
                    '''Setup SQLAlchemy database engine(s)'''
                    from sqlalchemy import engine_from_config
                    engine1 = engine_from_config(pylons_config, 'sqlalchemy.first.')
                    engine2 = engine_from_config(pylons_config, 'sqlalchemy.second.')
                    # engine1 should be assigned to sa_engine as well as your first engine's name
                    config['pylons.app_globals'].sa_engine = engine1
                    config['pylons.app_globals'].sa_engine_first = engine1
                    config['pylons.app_globals'].sa_engine_second = engine2
                    # Pass the engines to init_model, to be able to introspect tables
                    init_model(engine1, engine2)

            #base_config = AppConfig()
            base_config = MultiDBAppConfig()

        This will pull the config settings from your .ini files to create the necessary
        engines for use within your application.  Make sure you have a look at :ref:`multidatabase`
        for more information.

        """
        from sqlalchemy import engine_from_config
        engine = engine_from_config(pylons_config, 'sqlalchemy.')
        config['pylons.app_globals'].sa_engine = engine
        # Pass the engine to initmodel, to be able to introspect tables
        self.package.model.init_model(engine)

    def setup_auth(self):
        """
           Override this method to define how you would like the auth to be set up for your app.

           For the standard TurboGears App, this will set up the auth with SQLAlchemy.
        """
        if self.auth_backend == "sqlalchemy":
            self.setup_sa_auth_backend()

    def make_load_environment(self):
        """Return a load_environment function.

        The returned load_environment function can be called to configure
        the TurboGears runtime environment for this particular application.
        You can do this dynamically with multiple nested TG applications
        if necessary.

        """

        def load_environment(global_conf, app_conf):
            """Configure the Pylons environment via ``pylons.configuration.config``."""
            global_conf=Bunch(global_conf)
            app_conf=Bunch(app_conf)

            self.setup_paths()
            self.init_config(global_conf, app_conf)

            #Registers functions to be called at startup and shutdown
            #from self.call_on_startup and shutdown respectively.
            self.setup_startup_and_shutdown()

            self.setup_routes()
            self.setup_helpers_and_globals()
            self.setup_mimetypes()
            self.setup_auth()

            if not 'json' in self.renderers: self.renderers.append('json')

            for renderer in self.renderers:
                setup = getattr(self, 'setup_%s_renderer'%renderer, None)
                if setup:
                    setup()
                else:
                    raise Exception('This configuration object does not support the %s renderer'%renderer)


            if self.use_legacy_renderer:
                self.setup_default_renderer()

            self.setup_persistence()

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
        if 'sa_auth' in config:
            auth_args.update(config.sa_auth)
        if 'password_encryption_method' in auth_args:
            del auth_args['password_encryption_method']
        if not skip_authentication:
            if not 'cookie_secret' in auth_args.keys():
                msg = "base_config.sa_auth.cookie_secret is required "\
                "you must define it in app_cfg.py or set "\
                "sa_auth.cookie_secret in development.ini"
                raise TGConfigError(msg)
        app = setup_sql_auth(app, skip_authentication=skip_authentication,
                             **auth_args)
        return app

    def add_core_middleware(self, app):
        """Add support for routes dispatch, sessions, and caching.
        This is where you would want to override if you wanted to provide your
        own routing, session, or caching middleware.  Your app_cfg.py might look something
        like this::

            from tg.configuration import AppConfig
            from routes.middleware import RoutesMiddleware
            from beaker.middleware import CacheMiddleware
            from mysessionier.middleware import SessionMiddleware

            class MyAppConfig(AppConfig):
                def add_core_middleware(self, app):
                    app = RoutesMiddleware(app, config['routes.map'])
                    app = SessionMiddleware(app, config)
                    app = CacheMiddleware(app, config)
                    return app
            base_config = MyAppConfig()
        """
        app = RoutesMiddleware(app, config['routes.map'])
        app = SessionMiddleware(app, config)
        app = CacheMiddleware(app, config)
        return app

    def add_tosca_middleware(self, app):
        """Configure the ToscaWidgets middleware.

        If you would like to override the way the TW middleware works, you might do something like::

            from tg.configuration import AppConfig
            from tw.api import make_middleware as tw_middleware

            class MyAppConfig(AppConfig):

                def add_tosca2_middleware(self, app):

                    app = tw_middleware(app, {
                        'toscawidgets.framework.default_view': self.default_renderer,
                        'toscawidgets.framework.translator': ugettext,
                        'toscawidgets.middleware.inject_resources': False,
                        })
                    return app

            base_config = MyAppConfig()



        The above example would disable resource injection.

        There is more information about the settings you can change
        in the ToscaWidgets `middleware. <http://toscawidgets.org/documentation/ToscaWidgets/modules/middleware.html>`


        """

        from tw.api import make_middleware as tw_middleware


        twconfig = {'toscawidgets.framework.default_view': self.default_renderer,
                    'toscawidgets.framework.translator': ugettext,
                    'toscawidgets.middleware.inject_resources': True,
                    }
        for k,v in config.iteritems():
            if k.startswith('toscawidgets.framework.') or k.startswith('toscawidgets.middleware.'):
                twconfig[k] = v

        if 'toscawidgets.framework.resource_variant' in config:
            import tw.api
            tw.api.resources.registry.ACTIVE_VARIANT = config['toscawidgets.framework.resource_variant']
            #remove it from the middleware madness
            del twconfig['toscawidgets.framework.resource_variant']

        app = tw_middleware(app, twconfig)
        return app

    def add_tosca2_middleware(self, app):
        """Configure the ToscaWidgets2 middleware.

        If you would like to override the way the TW2 middleware works,
        you might do change your app_cfg.py to add something like::

            from tg.configuration import AppConfig
            from tw2.core.middleware import TwMiddleware

            class MyAppConfig(AppConfig):

                def add_tosca2_middleware(self, app):

                    app = TwMiddleware(app,
                        default_engine=self.default_renderer,
                        translator=ugettext,
                        auto_reload_templates = False
                        )

                    return app
            base_config = MyAppConfig()



        The above example would always set the template auto reloading off. (This is normally an
        option that is set within your application's ini file.)
        """
        from tw2.core.middleware import Config, TwMiddleware
        default_tw2_config = dict( default_engine=self.default_renderer,
                                   translator=ugettext,
                                   auto_reload_templates=asbool(self.get('templating.mako.reloadfromdisk', 'false'))
                                   )
        default_tw2_config.update(self.custom_tw2_config)
        app = TwMiddleware(app, **default_tw2_config)
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

            if self.use_toscawidgets2:
                app = self.add_tosca2_middleware(app)

            if self.auth_backend:
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

            if pylons_config.get('make_body_seekable'):
                app = maybe_make_body_seekable(app)

            if asbool(full_stack):
                if (self.auth_backend is None
                        and 401 not in self.handle_status_codes):
                    # If there's no auth backend configured which traps 401
                    # responses we redirect those responses to a nicely
                    # formatted error page
                    self.handle_status_codes.append(401)
                # This should never be true for internal nested apps
                app = self.add_error_middleware(global_conf, app)

            # Establish the registry for this application
            app = RegistryManager(app)

            # Static files (if running in production, and Apache or another
            # web server is serving static files)

            #if the user has set the value in app_config, don't pull it from the ini
            if not hasattr(self, 'serve_static'):
                self.serve_static = asbool(config.get('serve_static', 'true'))
            if self.serve_static:
                app = self.add_static_file_middleware(app)

            return app

        return make_base_app

def maybe_make_body_seekable(app):
    def wrapper(environ, start_response):
        log.debug("Making request body seekable")
        Request(environ).make_body_seekable()
        return app(environ, start_response)
    return wrapper
