"""
Testing for TG2 Configuration
"""
from nose import SkipTest
from nose.tools import eq_, raises
import atexit, sys, os

from tg.util import Bunch
from tg.configuration import AppConfig, config
from tg.configuration.app_config import TGConfigError
from tg.configuration.auth import _AuthenticationForgerPlugin
from tg.configuration.auth.metadata import _AuthMetadataAuthenticator
from tg.configuration.utils import coerce_config
from tg.configuration import milestones
from paste.deploy.converters import asint

import tg.i18n
from tg import TGController, expose, response, request, abort
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request
from webtest import TestApp
from tg.renderers.base import RendererFactory

from tg.wsgiapp import TGApp
from tg._compat import PY3

def setup():
    milestones._reset_all()
    setup_session_dir()
def teardown():
    milestones._reset_all()
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

class UncopiableList(list):
    """
    This is to test configuration methods that make a copy
    of a list to modify it, using this we can check how it has
    been modified
    """
    def __copy__(self):
        return self

class FakeTransaction:
    def get(self):
        return self

    def begin(self):
        self.aborted = False
        self.doomed = False

    def abort(self):
        self.aborted = True

    def commit(self):
        self.aborted = False

    def _retryable(self, *args):
        return True
    note = _retryable

    def isDoomed(self):
        return self.doomed

    def doom(self):
        self.doomed = True

from tg.configuration.auth import TGAuthMetadata
class ApplicationAuthMetadata(TGAuthMetadata):
    def get_user(self, identity, userid):
        return {'name':'None'}

class ApplicationAuthMetadataWithAuthentication(TGAuthMetadata):
    def authenticate(self, environ, identity):
        return 1
    def get_user(self, identity, userid):
        return {'name':'None'}

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

def test_coerce_config():
    conf = coerce_config({'ming.connection.max_pool_size':'5'}, 'ming.connection.', {'max_pool_size':asint})
    assert conf['max_pool_size'] == 5

class TestAppConfig:
    def __init__(self):
        self.fake_package = PackageWithModel

    def setup(self):
        milestones._reset_all()

        self.config = AppConfig()
        # set up some required paths and config settings
        # FIXME: these seem to be needed so that
        # other tests don't suffer - but that's a nasty
        # side-effect. setup for those tests actually needs
        # fixing.
        self.config.package = self.fake_package
        self.config['paths']['root'] = 'test'
        self.config['paths']['controllers'] = 'test.controllers'
        self.config._init_config({'cache_dir':'/tmp'}, {})

        config['paths']['static_files'] = "test"
        config["tg.app_globals"] = Bunch()
        config["use_sqlalchemy"] = False
        config["global_conf"] = Bunch()
        config["package"] = "test"
        config["render_functions"] = Bunch()
        config['beaker.session.secret'] = 'some_secret'

    def teardown(self):
        #This is here to avoid that other tests keep using the forced controller
        config.pop('tg.root_controller', None)
        milestones._reset_all()

    def test_get_root(self):
        current_root_module = self.config['paths']['root']
        assert self.config.get_root_module() == 'tests.controllers.root', self.config.get_root_module()
        self.config['paths']['root'] = None
        assert self.config.get_root_module() == None, self.config.get_root_module()
        self.config['paths']['root'] = current_root_module

    def test_lang_can_be_changed_by_ini(self):
        conf = AppConfig(minimal=True)
        conf._init_config({'lang':'ru'}, {})
        assert config['lang'] == 'ru'

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
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_callable_startup_with_exception(self):
        def func():
            raise Exception
        self.config.call_on_startup = [func]
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_startup_not_callable(self):
        self.config.call_on_startup = ['not callable']
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_shutdown_not_callable(self):
        self.config.call_on_shutdown = ['not callable']
        self.config._setup_startup_and_shutdown()

    def test_setup_startup_and_shutdown_shutdown_callable(self):
        def func():
            raise AtExitTestException()

        _registered_exit_funcs = []
        def _fake_atexit_register(what):
            _registered_exit_funcs.append(what)

        _real_register = atexit.register
        atexit.register = _fake_atexit_register

        try:
            self.config.call_on_shutdown = [func]
            self.config._setup_startup_and_shutdown()
        finally:
            atexit.register = _real_register

        assert func in _registered_exit_funcs, _registered_exit_funcs

    def test_setup_helpers_and_globals(self):
        self.config.setup_helpers_and_globals()

    def test_setup_sa_auth_backend(self):
        class ConfigWithSetupAuthBackend(self.config.__class__):
            called = []

            def setup_sa_auth_backend(self):
                self.called.append(True)

        conf = ConfigWithSetupAuthBackend()
        conf.setup_auth()

        assert len(ConfigWithSetupAuthBackend.called) >= 1

    def test_setup_jinja_without_package(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.renderers = ['jinja']
        app = conf.make_wsgi_app()

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

    def test_custom_transaction_manager(self):
        class CustomAppConfig(AppConfig):
            def add_tm_middleware(self, app):
                self.did_perform_custom_tm = True
                return app

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        package = PackageWithModel()
        conf = CustomAppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'

        app = conf.make_wsgi_app()

        assert conf.did_perform_custom_tm == True
        assert conf.application_wrappers == []

    def test_sqlalchemy_commit_veto(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

            @expose()
            def crash(self):
                raise Exception('crash')

            @expose()
            def forbidden(self):
                response.status = 403
                return 'FORBIDDEN'

            @expose()
            def notfound(self):
                response.status = 404
                return 'NOTFOUND'

        def custom_commit_veto(environ, status, headers):
            if status.startswith('404'):
                return True
            return False

        fake_transaction = FakeTransaction()
        import transaction
        prev_transaction_manager = transaction.manager
        transaction.manager = fake_transaction

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'
        conf.commit_veto = custom_commit_veto

        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test')
        assert fake_transaction.aborted == False

        try:
            app.get('/crash')
        except:
            pass
        assert fake_transaction.aborted == True

        app.get('/forbidden', status=403)
        assert fake_transaction.aborted == False

        app.get('/notfound', status=404)
        assert fake_transaction.aborted == True

        transaction.manager = prev_transaction_manager

    def test_sqlalchemy_doom(self):
        fake_transaction = FakeTransaction()
        import transaction
        prev_transaction_manager = transaction.manager
        transaction.manager = fake_transaction

        class RootController(TGController):
            @expose()
            def test(self):
                fake_transaction.doom()
                return 'HI!'

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'

        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test')
        assert fake_transaction.aborted == True

        transaction.manager = prev_transaction_manager

    def test_sqlalchemy_retry(self):
        fake_transaction = FakeTransaction()
        import transaction
        prev_transaction_manager = transaction.manager
        transaction.manager = fake_transaction

        from transaction.interfaces import TransientError

        class RootController(TGController):
            attempts = []

            @expose()
            def test(self):
                self.attempts.append(True)
                if len(self.attempts) == 3:
                    return 'HI!'
                raise TransientError()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf.use_transaction_manager = True
        conf['sqlalchemy.url'] = 'sqlite://'
        conf['tm.attempts'] = 3

        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        assert 'HI' in resp

        transaction.manager = prev_transaction_manager

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

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://'
        conf['ming.db'] = 'inmemdb'

        app = conf.make_wsgi_app()
        assert app is not None

    def test_setup_ming_persistance_with_url_alone(self):
        if PY3: raise SkipTest()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://inmemdb'

        app = conf.make_wsgi_app()
        assert app is not None

    def test_setup_ming_persistance_advanced_options(self):
        if PY3: raise SkipTest()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://inmemdb'
        conf['ming.connection.read_preference'] = 'PRIMARY'

        app = conf.make_wsgi_app()
        assert app is not None

    def test_add_auth_middleware(self):
        class Dummy:pass

        self.config.sa_auth.dbsession = Dummy()
        self.config.sa_auth.user_class = Dummy
        self.config.sa_auth.group_class = Dummy
        self.config.sa_auth.permission_class = Dummy
        self.config.sa_auth.cookie_secret = 'dummy'
        self.config.sa_auth.password_encryption_method = 'sha'

        self.config.setup_auth()
        self.config.add_auth_middleware(None, None)

    def test_add_static_file_middleware(self):
        self.config.add_static_file_middleware(None)

    def test_setup_sqla_auth(self):
        if PY3: raise SkipTest()

        class RootController(TGController):
            @expose()
            def test(self):
                return str(request.environ)

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.auth_backend = 'sqlalchemy'
        conf.use_sqlalchemy = True
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                           'dbsession': None,
                           'user_class': None,
                           'cookie_secret':'12345'}
        conf['sqlalchemy.url'] = 'sqlite://'
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'repoze.who.plugins' in app.get('/test')

        self.config.auth_backend = None

    def test_setup_ming_auth(self):
        self.config.auth_backend = 'ming'

        self.config.setup_auth()
        assert 'sa_auth' in config

        self.config.auth_backend = None

    def test_register_hooks(self):
        def dummy(*args):
            pass

        milestones.config_ready._reset()
        milestones.environment_loaded._reset()
 
        self.config.register_hook('startup', dummy)
        self.config.register_hook('shutdown', dummy)
        self.config.register_hook('controller_wrapper', dummy)
        for hook_name in self.config.hooks.keys():
            self.config.register_hook(hook_name, dummy)

        milestones.config_ready.reach()
        milestones.environment_loaded.reach()

        for hooks in self.config.hooks.values():
            assert hooks

        assert self.config.call_on_startup
        assert self.config.call_on_shutdown
        assert self.config.controller_wrappers

    @raises(TGConfigError)
    def test_missing_secret(self):
        self.config.auth_backend = 'sqlalchemy'
        config.pop('beaker.session.secret', None)
        self.config.setup_auth()

    def test_controler_wrapper_setup(self):
        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = []
        self.config._setup_controller_wrappers()
        assert config['controller_caller'] == orig_caller

        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                return caller(*args, **kw)
            return call

        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = [controller_wrapper]
        self.config._setup_controller_wrappers()
        assert config['controller_caller'].__name__ == controller_wrapper(self.config, orig_caller).__name__

    def test_global_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_hook('controller_wrapper', controller_wrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True

    def test_dedicated_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.wrap_controller(controller_wrapper, controller=RootController.test)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True

    def test_mixed_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        app_wrapper_has_been_visited = []
        def app_controller_wrapper(app_config, caller):
            def call(*args, **kw):
                app_wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        wrapper_has_been_visited = []
        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.wrap_controller(app_controller_wrapper)
        tg.hooks.wrap_controller(controller_wrapper, controller=RootController.test)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True
        assert app_wrapper_has_been_visited[0] is True

    def test_application_wrapper_setup(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        class AppWrapper(object):
            def __init__(self, dispatcher):
                self.dispatcher = dispatcher
            def __call__(self, *args, **kw):
                wrapper_has_been_visited.append(True)
                return self.dispatcher(*args, **kw)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_wrapper(AppWrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] == True

    def test_application_wrapper_ordering_after(self):
        class AppWrapper1:
            pass
        class AppWrapper2:
            pass
        class AppWrapper3:
            pass
        class AppWrapper4:
            pass
        class AppWrapper5:
            pass

        conf = AppConfig(minimal=True)
        conf.register_wrapper(AppWrapper2)
        conf.register_wrapper(AppWrapper4, after=AppWrapper3)
        conf.register_wrapper(AppWrapper3)
        conf.register_wrapper(AppWrapper1, after=False)
        conf.register_wrapper(AppWrapper5, after=AppWrapper3)
        milestones.environment_loaded.reach()

        assert conf.application_wrappers[0] == AppWrapper1
        assert conf.application_wrappers[1] == AppWrapper2
        assert conf.application_wrappers[2] == AppWrapper3
        assert conf.application_wrappers[3] == AppWrapper4
        assert conf.application_wrappers[4] == AppWrapper5

    @raises(TGConfigError)
    def test_application_wrapper_blocked_after_milestone(self):
        class AppWrapper1:
            pass
        class AppWrapper2:
            pass

        conf = AppConfig(minimal=True)
        conf.register_wrapper(AppWrapper1)
        milestones.environment_loaded.reach()
        conf.register_wrapper(AppWrapper2)

    def test_wrap_app(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        middleware_has_been_visited = []
        class AppWrapper(object):
            def __init__(self, app):
                self.app = app
            def __call__(self, environ, start_response):
                middleware_has_been_visited.append(True)
                return self.app(environ, start_response)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app(wrap_app=AppWrapper)
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert middleware_has_been_visited[0] == True

    def test_unsupported_renderer(self):
        renderers = self.config.renderers
        self.config.renderers = ['unknwon']
        try:
            self.config._setup_renderers()
        except TGConfigError:
            self.config.renderers = renderers
        else:
            assert False

    @raises(TGConfigError)
    def test_cookie_secret_required(self):
        self.config.sa_auth = {}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, False)

    def test_sqla_auth_middleware(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_using_translations(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'translations': {'user_name':'SomethingElse'},
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        auth = None
        for authname, authobj in self.config['sa_auth']['authenticators']:
            if authname == 'sqlauth':
                auth = authobj
                break

        assert auth is not None, self.config['sa_auth']['authenticators']
        assert auth.translations['user_name'] == 'SomethingElse', auth.translations

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_default_after(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'cookie_secret':'12345',
                                  'dbsession': None,
                                  'user_class': None,
                                  'authenticators':UncopiableList([('superfirst', None),
                                                                   ('default', None)])}

        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert authenticators[1] == 'superfirst'
        assert 'cookie' in authenticators
        assert 'sqlauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_no_authenticators(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'dbsession': None,
                                  'user_class': None,
                                  'cookie_secret':'12345'}

        #In this case we can just test it doesn't crash
        #as the sa_auth dict doesn't have an authenticators key to check for
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_sqla_auth_middleware_only_mine(self):
        past_config_sa_auth = config.sa_auth
        config.sa_auth = {}

        class RootController(TGController):
            @expose()
            def test(self):
                return str(request.environ)

            @expose()
            def forbidden(self):
                response.status = "401"

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.auth_backend = 'sqlalchemy'
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'

        alwaysadmin = _AuthenticationForgerPlugin(fake_user_key='FAKE_USER')
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                           'cookie_secret':'12345',
                           'form_plugin':alwaysadmin,
                           'authenticators':UncopiableList([('alwaysadmin', alwaysadmin)]),
                           'identifiers':[('alwaysadmin', alwaysadmin)],
                           'challengers':[]}

        app = conf.make_wsgi_app()

        authenticators = [x[0] for x in conf['sa_auth']['authenticators']]
        assert authenticators[0] == 'alwaysadmin'
        assert 'sqlauth' not in authenticators

        challengers = [x[1] for x in conf['sa_auth']['challengers']]
        assert alwaysadmin in challengers

        app = TestApp(app)
        assert 'repoze.who.identity' in app.get('/test', extra_environ={'FAKE_USER':'admin'})
        assert app.get('/forbidden', status=401)

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth

    def test_sqla_auth_logging_stderr(self):
        past_config_sa_auth = config.sa_auth
        config.sa_auth = {}

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.auth_backend = 'sqlalchemy'
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'

        alwaysadmin = _AuthenticationForgerPlugin(fake_user_key='FAKE_USER')
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                           'cookie_secret':'12345',
                           'form_plugin':alwaysadmin,
                           'log_level':'DEBUG',
                           'authenticators':UncopiableList([('alwaysadmin', alwaysadmin)]),
                           'identifiers':[('alwaysadmin', alwaysadmin)],
                           'challengers':[]}

        conf['sa_auth']['log_file'] = 'stderr'
        app = conf.make_wsgi_app()
        conf['sa_auth']['log_file'] = 'stdout'
        app = conf.make_wsgi_app()

        import tempfile
        f = tempfile.NamedTemporaryFile()
        conf['sa_auth']['log_file'] = f.name
        app = conf.make_wsgi_app()

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth

    def test_ming_auth_middleware(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'ming'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
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
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'cookie_secret':'12345'}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert len(authenticators) == 1

        self.config['sa_auth'] = {}
        self.config.auth_backend = None
        config.sa_auth = past_config_sa_auth

    def test_tgauthmetadata_auth_middleware(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'tgappauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_auth_middleware_doesnt_touch_authenticators(self):
        # Checks that the auth middleware process doesn't touch original authenticators
        # list, to prevent regressions on this.
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':[('default', None)]}
        self.config.setup_auth()
        self.config.add_auth_middleware(None, True)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert len(authenticators) == 1

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_tgauthmetadata_loginpwd(self):
        who_authenticator = _AuthMetadataAuthenticator(ApplicationAuthMetadataWithAuthentication(), using_password=True)
        assert who_authenticator.authenticate({}, {}) == None

    def test_tgauthmetadata_nologinpwd(self):
        who_authenticator = _AuthMetadataAuthenticator(ApplicationAuthMetadataWithAuthentication(), using_password=False)
        assert who_authenticator.authenticate({}, {}) == 1

    def test_toscawidgets_recource_variant(self):
        if PY3: raise SkipTest()

        resultingconfig = {}

        def fake_make_middleware(app, twconfig):
            resultingconfig.update(twconfig)
            return app

        import tw.api
        prev_tw_make_middleware = tw.api.make_middleware

        tw.api.make_middleware = fake_make_middleware
        config['toscawidgets.framework.resource_variant'] = 'min'
        self.config.add_tosca_middleware(None)
        config.pop('toscawidgets.framework.resource_variant', None)
        tw.api.make_middleware = prev_tw_make_middleware

        assert resultingconfig['toscawidgets.framework.default_view'] == self.config.default_renderer
        assert resultingconfig['toscawidgets.framework.translator'] == tg.i18n.ugettext
        assert resultingconfig['toscawidgets.middleware.inject_resources'] == True
        assert tw.api.resources.registry.ACTIVE_VARIANT == 'min'

    def test_config_hooks(self):
        # Reset milestone so that registered hooks
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        visited_hooks = []
        def before_config_hook(app):
            visited_hooks.append('before_config')
            return app
        def after_config_hook(app):
            visited_hooks.append('after_config')
            return app

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_hook('before_config', before_config_hook)
        conf.register_hook('after_config', after_config_hook)
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert 'before_config' in visited_hooks
        assert 'after_config' in visited_hooks

    def test_controller_hooks_with_value(self):
        # Reset milestone so that registered hooks
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return tg.hooks.notify_with_value('test_hook', 'BO',
                                                  controller=RootController.test)

        def value_hook(value):
            return value*2

        tg.hooks.register('test_hook', value_hook, controller=RootController.test)

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        assert 'BOBO' in resp, resp

    @raises(TGConfigError)
    def test_config_hooks_startup_on_controller(self):
        def f():
            pass

        tg.hooks.register('startup', None, controller=f)

    @raises(TGConfigError)
    def test_config_hooks_shutdown_on_controller(self):
        def f():
            pass

        tg.hooks.register('shutdown', None, controller=f)

    @raises(TGConfigError)
    def test_controller_wrapper_using_register(self):
        milestones.config_ready.reach()
        tg.hooks.register('controller_wrapper', None)

    @raises(TGConfigError)
    def test_global_controller_wrapper_after_milestone_reached(self):
        milestones.environment_loaded.reach()
        tg.hooks.wrap_controller(None)

    @raises(TGConfigError)
    def test_dedicated_controller_wrapper_after_milestone_reached(self):
        milestones.environment_loaded.reach()

        def f():
            pass

        tg.hooks.wrap_controller(None, controller=f)

    def test_error_middleware_disabled_with_optimize(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()

        os.environ['PYTHONOPTIMIZE'] = '2'
        app = conf.make_wsgi_app()
        os.environ.pop('PYTHONOPTIMIZE')

        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    def test_serve_statics(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        conf.serve_static = True
        app = conf.make_wsgi_app()
        assert app.__class__.__name__.startswith('Statics')

        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    def test_mount_point_with_minimal(self):
        class SubController(TGController):
            @expose()
            def test(self):
                return self.mount_point

        class RootController(TGController):
            sub = SubController()

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()

        app = TestApp(app)
        assert '/sub' in app.get('/sub/test')

    def test_application_test_vars(self):
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app(global_conf={'debug':True})
        app = TestApp(app)

        assert 'DONE' in app.get('/_test_vars')
        assert request.path == '/_test_vars'

    def test_application_empty_controller(self):
        class RootController(object):
            def __call__(self, environ, start_response):
                return None

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app(global_conf={'debug':True})
        app = TestApp(app)

        r = app.get('/something', status=500)
        assert 'No content returned by controller' in r

    def test_application_test_mode_detection(self):
        class FakeRegistry(object):
            def register(self, *args, **kw):
                pass

        a = TGApp()
        testmode, __ = a.setup_app_env({'paste.registry':FakeRegistry()})
        assert testmode is False

        testmode, __ = a.setup_app_env({'paste.registry':FakeRegistry(),
                                        'paste.testing_variables':{}})
        assert testmode is True

    def test_application_no_controller_hijacking(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        class AppWrapper(object):
            def __init__(self, dispatcher):
                self.dispatcher = dispatcher
            def __call__(self, controller, environ, start_response):
                return self.dispatcher(None, environ, start_response)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.application_wrappers.append(AppWrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test', status=404)

    def test_package_no_app_globals(self):
        class RootController(TGController):
            pass

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = sys.modules[__name__]

        app = conf.make_wsgi_app()

    def test_custom_error_document(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                abort(403)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.handle_error_page = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' in resp, resp

    def test_custom_error_document_with_streamed_response(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                response.status_code = 403
                def _output():
                    yield 'Hi'
                    yield 'World'
                return _output()

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.handle_error_page = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' in resp, resp

    def test_errorware_configuration(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HI'

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app(global_conf={'trace_errors.error_email': 'test@domain.com'},
                                 full_stack=True)
        app = TestApp(app)

        resp = app.get('/test')
        assert 'HI' in resp, resp

        assert config['tg.errorware']['error_email'] == 'test@domain.com'
        assert config['tg.errorware']['error_subject_prefix'] == 'WebApp Error: '
        assert config['tg.errorware']['error_message'] == 'An internal server error occurred'

    def test_tw2_unsupported_renderer(self):
        import tw2.core

        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                rl = tw2.core.core.request_local()
                tw2conf = rl['middleware'].config
                return ','.join(tw2conf.preferred_rendering_engines)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.prefer_toscawidgets2 = True
        conf.renderers = ['kajiki', 'genshi']
        conf.default_renderer = 'kajiki'

        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test')
        assert 'genshi' in resp, resp

    def test_tw2_renderers_preference(self):
        import tw2.core

        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                rl = tw2.core.core.request_local()
                tw2conf = rl['middleware'].config
                return ','.join(tw2conf.preferred_rendering_engines)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.prefer_toscawidgets2 = True
        conf.renderers = ['genshi']
        conf.default_renderer = 'genshi'

        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test')
        assert 'genshi' in resp, resp

    def test_tw2_unsupported(self):
        import tw2.core

        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                rl = tw2.core.core.request_local()
                tw2conf = rl['middleware'].config
                return ','.join(tw2conf.preferred_rendering_engines)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.prefer_toscawidgets2 = True
        conf.renderers = ['kajiki']
        conf.default_renderer = 'kajiki'

        try:
            app = conf.make_wsgi_app(full_stack=True)
            assert False
        except TGConfigError as e:
            assert 'None of the configured rendering engines is supported' in str(e)

    def test_backward_compatible_engine_failed_setup(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        def setup_broken_renderer():
            return False

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.setup_broken_renderer = setup_broken_renderer
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json']

    def test_backward_compatible_engine_success_setup(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        conf = AppConfig(minimal=True, root_controller=RootController())

        def setup_broken_renderer():
            conf.render_functions.broken = 'BROKEN'
            return True

        conf.setup_broken_renderer = setup_broken_renderer
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json', 'broken']
        assert conf.render_functions.broken == 'BROKEN'

    def test_render_factory_success(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        class FailedFactory(RendererFactory):
            engines = {'broken': {'content_type': 'text/plain'}}

            @classmethod
            def create(cls, config, app_globals):
                return {'broken': 'BROKEN'}

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_rendering_engine(FailedFactory)
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json', 'broken']
        assert conf.render_functions.broken == 'BROKEN'

    def test_render_factory_failure(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HELLO'

        class FailedFactory(RendererFactory):
            engines = {'broken': {'content_type': 'text/plain'}}

            @classmethod
            def create(cls, config, app_globals):
                return None

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_rendering_engine(FailedFactory)
        conf.renderers = ['json', 'broken']

        app = conf.make_wsgi_app(full_stack=True)
        assert conf.renderers == ['json']

