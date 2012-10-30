"""
Testing for TG2 Configuration
"""
from nose import SkipTest
from nose.tools import eq_, raises
import atexit, sys

from tg.util import Bunch
from tg.configuration import AppConfig, config
from tg.configuration.app_config import TGConfigError
from tg import TGController, expose
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request
from webtest import TestApp

from tg.wsgiapp import TGApp
from tg._compat import PY3


def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

class PackageWithModel:
    __name__ = 'tests'
    __file__ = __file__

    def __init__(self):
        self.model = self.ModelClass()
        self.model.DBSession = self.model.FakeDBSession()

    class ModelClass:
        class FakeDBSession:
            def remove(self):
                self.DBSESSION_REMOVED=True

        @classmethod
        def init_model(package, engine):
            pass

    class lib:
        class app_globals:
            class Globals:
                pass
PackageWithModel.__name__ = 'tests'

from tg.configuration.auth import TGAuthMetadata
class ApplicationAuthMetadata(TGAuthMetadata):
    def __init__(self, sa_auth):
        self.sa_auth = sa_auth
    def get_user(self, identity, userid):
        return None
    def get_groups(self, identity, userid):
        return []
    def get_permissions(self, identity, userid):
        return []


class AtExitTestException(Exception):
    pass

class TestPylonsConfigWrapper:

    def setup(self):
        self.config = config

    def test_create(self):
        pass

    def test_getitem(self):
        expected_keys = ['global_conf', 'use_sqlalchemy', 'package', 'tg.app_globals', 'call_on_shutdown']
        for key in expected_keys:
            self.config[key]

    @raises(KeyError)
    def test_getitem_bad(self):
        self.config['no_such_key']

    def test_setitem(self):
        self.config['no_such_key'] = 'something'

    def test_delattr(self):
        del self.config.use_sqlalchemy
        eq_(hasattr(self.config, 'use_sqlalchemy'), False)
        self.config.use_sqlalchemy = True

    @raises(AttributeError)
    def test_delattr_bad(self):
        del self.config.i_dont_exist

    def test_keys(self):
        k = self.config.keys()
        assert 'tg.app_globals' in k

class TestAppConfig:
    def __init__(self):
        self.fake_package = PackageWithModel

    def setup(self):
        self.config = AppConfig()
        # set up some required paths and config settings
        # FIXME: these seem to be needed so that
        # other tests don't suffer - but that's a nasty
        # side-effect. setup for those tests actually needs
        # fixing.
        self.config.package = self.fake_package
        self.config['paths']['root'] = 'test'
        self.config['paths']['controllers'] = 'test.controllers'
        self.config.init_config({'cache_dir':'/tmp'}, {})

        config['paths']['static_files'] = "test"
        config["tg.app_globals"] = Bunch()
        config["use_sqlalchemy"] = False
        config["global_conf"] = Bunch()
        config["package"] = "test"
        config["call_on_shutdown"] = "foo"
        config["render_functions"] = Bunch()
        config['beaker.session.secret'] = 'some_secret'

    def teardown(self):
        #This is here to avoid that other tests keep using the forced controller
        config.pop('tg.root_controller', None)

    def test_get_root(self):
        current_root_module = self.config['paths']['root']
        assert self.config.get_root_module() == 'tests.controllers.root', self.config.get_root_module()
        self.config['paths']['root'] = None
        assert self.config.get_root_module() == None, self.config.get_root_module()
        self.config['paths']['root'] = current_root_module

    def test_create_minimal_app(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

        #This is here to avoid that other tests keep using the forced controller
        config.pop('tg.root_controller')

    def test_amf_initialization(self):
        conf = AppConfig(minimal=True)
        conf.renderers.append('amf')
        app = conf.make_wsgi_app()
        assert 'amf' not in conf.renderers

    def test_enable_routes(self):
        if PY3: raise SkipTest()

        conf = AppConfig(minimal=True)
        conf.enable_routes = True
        app = conf.make_wsgi_app()

        a = TGApp()
        assert a.enable_routes == True

        config.pop('routes.map')
        config.pop('enable_routes')

    def test_create(self):
        pass

    def test_setup_startup_and_shutdown_startup_callable(self):
        def func():
            a = 7
        self.config.call_on_startup = [func]
        self.config.setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_callable_startup_with_exception(self):
        def func():
            raise Exception
        self.config.call_on_startup = [func]
        self.config.setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_startup_not_callable(self):
        self.config.call_on_startup = ['not callable']
        self.config.setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_shutdown_not_callable(self):
        self.config.call_on_shutdown = ['not callable']
        self.config.setup_startup_and_shutdown()

    @raises(AtExitTestException)
    def test_setup_startup_and_shutdown_shutdown_callable(self):
        def func():
            raise AtExitTestException()

        self.config.call_on_shutdown = [func]
        self.config.setup_startup_and_shutdown()
        atexit._run_exitfuncs()

    def test_setup_helpers_and_globals(self):
        self.config.setup_helpers_and_globals()

    def test_setup_sa_auth_backend(self):
        self.config.setup_sa_auth_backend()

    def test_setup_chameleon_genshi_renderer(self):
        if PY3: raise SkipTest()

        self.config.paths.templates = 'template_path'
        self.config.setup_chameleon_genshi_renderer()

    def test_setup_kajiki_renderer(self):
        if PY3: raise SkipTest()

        self.config.paths.templates = 'template_path'
        self.config.setup_kajiki_renderer()

    def test_setup_genshi_renderer(self):
        self.config.paths.templates = 'template_path'
        self.config.setup_genshi_renderer()

    def test_setup_jinja_renderer(self):
        self.config.paths.templates = 'template_path'
        self.config.setup_jinja_renderer()

    def test_setup_mako_renderer(self):
        self.config.paths.templates = ['template_path']
        self.config.setup_mako_renderer(use_dotted_templatenames=True)
    
    def test_setup_sqlalchemy(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert package.model.DBSession.DBSESSION_REMOVED

    def test_setup_sqla_persistance(self):
        config['sqlalchemy.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config.setup_persistence()

        self.config.use_sqlalchemy = False

    def test_setup_sqla_balanced(self):
        config['sqlalchemy.master.url'] = 'sqlite://'
        config['sqlalchemy.slaves.slave1.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config.setup_persistence()

        self.config.use_sqlalchemy = False
        config.pop('sqlalchemy.master.url')
        config.pop('sqlalchemy.slaves.slave1.url')

    @raises(TGConfigError)
    def test_setup_sqla_balanced_prevent_slave_named_master(self):
        config['sqlalchemy.master.url'] = 'sqlite://'
        config['sqlalchemy.slaves.master.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        try:
            self.config.setup_persistence()
        except:
            raise
        finally:
            self.config.use_sqlalchemy = False
            config.pop('sqlalchemy.master.url')
            config.pop('sqlalchemy.slaves.master.url')

    @raises(TGConfigError)
    def test_setup_sqla_balanced_no_slaves(self):
        config['sqlalchemy.master.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        try:
            self.config.setup_persistence()
        except:
            raise
        finally:
            self.config.use_sqlalchemy = False
            config.pop('sqlalchemy.master.url')

    def test_setup_ming_persistance(self):
        if PY3: raise SkipTest()

        config['ming.url'] = 'mim://'
        config['ming.db'] = 'inmemdb'
        self.config.use_ming = True

        self.config.package = PackageWithModel()
        self.config.setup_persistence()

        self.config.use_ming = False

    def test_add_auth_middleware(self):
        class Dummy:pass

        self.config.sa_auth.dbsession = Dummy()
        self.config.sa_auth.user_class = Dummy
        self.config.sa_auth.group_class = Dummy
        self.config.sa_auth.permission_class = Dummy
        self.config.sa_auth.cookie_secret = 'dummy'
        self.config.sa_auth.password_encryption_method = 'sha'

        self.config.add_auth_middleware(None, None)

    def test_add_static_file_middleware(self):
        self.config.add_static_file_middleware(None)

    def test_setup_sqla_auth(self):
        self.config.auth_backend = 'sqlalchemy'

        self.config.setup_auth()
        assert 'sa_auth' in config

        self.config.auth_backend = None

    def test_setup_ming_auth(self):
        self.config.auth_backend = 'ming'

        self.config.setup_auth()
        assert 'sa_auth' in config

        self.config.auth_backend = None

    def test_register_hooks(self):
        def dummy(*args):
            pass

        self.config.register_hook('startup', dummy)
        self.config.register_hook('shutdown', dummy)
        self.config.register_hook('controller_wrapper', dummy)
        for hook_name in self.config.hooks.keys():
            self.config.register_hook(hook_name, dummy)

        for hooks in self.config.hooks.values():
            assert hooks

        assert self.config.call_on_startup
        assert self.config.call_on_shutdown
        assert self.config.controller_wrappers

    @raises(TGConfigError)
    def test_missing_secret(self):
        del config['beaker.session.secret']
        self.config.setup_sa_auth_backend()

    def test_controler_wrapper_setup(self):
        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = []
        self.config.setup_controller_wrappers()
        assert config['controller_caller'] == orig_caller

        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                return caller(*args, **kw)
            return call

        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = [controller_wrapper]
        self.config.setup_controller_wrappers()
        assert config['controller_caller'].__name__ == controller_wrapper(self.config, orig_caller).__name__

    def test_unsupported_renderer(self):
        renderers = self.config.renderers
        self.config.renderers = ['unknwon']
        try:
            self.config.setup_renderers()
        except TGConfigError:
            self.config.renderers = renderers
        else:
            assert False

    @raises(TGConfigError)
    def test_cookie_secret_required(self):
        self.config['sa_auth'] = {}
        self.config.add_auth_middleware(None, False)

    def test_sqla_auth_middleware(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(self.config.sa_auth),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':[('default', None)]}
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_default_after(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(self.config.sa_auth),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':[('superfirst', None), ('default', None)]}
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert authenticators[1] == 'superfirst'
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_no_authenticators(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(self.config.sa_auth),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345'}

        #In this case we can just test it doesn't crash
        #as the sa_auth dict doesn't have an authenticators key to check for
        self.config.add_auth_middleware(None, True)
        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_only_mine(self):
        past_config_sa_auth = config.sa_auth
        config.sa_auth = {}

        self.config.auth_backend = None
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(self.config.sa_auth),
                                  'cookie_secret':'12345',
                                  'authenticators':[('superfirst', None)]}
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert authenticators[1] == 'superfirst'
        assert 'sqlauth' not in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth

    def test_ming_auth_middleware(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'ming'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(self.config.sa_auth),
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':[('default', None)]}
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'mingauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    @raises(KeyError)
    def test_sqla_auth_middleware_no_backend(self):
        #This is expected to raise error as no authenticators are specified for a custom backend
        past_config_sa_auth = config.sa_auth
        config.sa_auth = {}

        self.config.auth_backend = None
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(self.config.sa_auth),
                                  'cookie_secret':'12345'}
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth