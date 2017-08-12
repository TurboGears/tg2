"""
Testing for TG2 Configuration
"""
from nose import SkipTest
from nose.tools import eq_, raises
import atexit, sys, os
from datetime import datetime
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import Engine
from ming import Session
from ming.orm import ThreadLocalORMSession
from tg.configuration.hooks import _TGGlobalHooksNamespace

from tg.appwrappers.errorpage import ErrorPageApplicationWrapper
from tg.appwrappers.mingflush import MingApplicationWrapper
from tg.appwrappers.transaction_manager import TransactionApplicationWrapper

from tg.util import Bunch
from tg.configuration import AppConfig, config
from tg.configuration.app_config import TGConfigError, defaults as app_config_defaults
from tg.configuration.auth import _AuthenticationForgerPlugin
from tg.configuration.auth.metadata import _AuthMetadataAuthenticator
from tg.configuration.utils import coerce_config, coerce_options
from tg.configuration import milestones
from tg.support.converters import asint, asbool

import tg.i18n
from tg import TGController, expose, response, request, abort
from tests.base import setup_session_dir, teardown_session_dir
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

        def init_model(self, engine):
            if isinstance(engine, Engine):
                # SQLA
                return self.DBSession
            else:
                # Ming
                return dict(ming=True)

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
        return self

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
    opts = {'ming.connection.max_pool_size': '5'}
    conf = coerce_config(opts, 'ming.connection.', {'max_pool_size':asint})
    assert conf['max_pool_size'] == 5
    assert opts['ming.connection.max_pool_size'] == '5'


def test_coerce_options():
    opts = {'connection': 'false'}
    conf = coerce_options(opts, {'connection': asbool})
    assert conf['connection'] is False
    assert opts['connection'] == 'false'


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
        self.config['package'] = self.fake_package
        self.config['paths']['root'] = 'test'
        self.config['paths']['controllers'] = 'test.controllers'
        self.config['paths']['static_files'] = "test"
        self.config["tg.app_globals"] = Bunch()
        self.config["use_sqlalchemy"] = False
        self.config["global_conf"] = Bunch()
        self.config["render_functions"] = Bunch()
        self.config['session.secret'] = 'some_secret'
        self.config._init_config({'cache_dir':'/tmp'}, {})


    def teardown(self):
        #This is here to avoid that other tests keep using the forced controller
        config.pop('tg.root_controller', None)
        milestones._reset_all()
        tg.hooks = _TGGlobalHooksNamespace()  # Reset hooks

    def test_reqlocal_configuration_dictionary(self):
        self.config['RANDOM_VALUE'] = 5
        conf = self.config._init_config({}, {})

        assert config['RANDOM_VALUE'] == 5
        assert len(config) == len(conf)

    def test_get_root(self):
        current_root_module = self.config['paths']['root']
        assert self.config._get_root_module() == 'tests.controllers.root', self.config._get_root_module()
        self.config['paths']['root'] = None
        assert self.config._get_root_module() == None, self.config._get_root_module()
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

    def test_minimal_app_with_sqlalchemy(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        DBSession = scoped_session(sessionmaker(autoflush=True, autocommit=False))
        def init_model(engine):
            DBSession.configure(bind=engine)

        conf = AppConfig(minimal=True, root_controller=RootController())

        conf['use_sqlalchemy'] = True
        conf['sqlalchemy.url'] = 'sqlite://'
        conf['model'] = Bunch(DBSession=DBSession,
                              init_model=init_model)

        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    @raises(TGConfigError)
    def test_sqlalchemy_without_models(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['use_sqlalchemy'] = True
        conf['sqlalchemy.url'] = 'sqlite://'
        app = conf.make_wsgi_app()

    def test_minimal_app_with_ming(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        mainsession = Session()
        DBSession = ThreadLocalORMSession(mainsession)

        def init_model(engine):
            mainsession.bind = engine

        conf = AppConfig(minimal=True, root_controller=RootController())

        conf['use_ming'] = True
        conf['ming.url'] = 'mim://'
        conf['model'] = Bunch(init_model=init_model, DBSession=DBSession)

        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    @raises(TGConfigError)
    def test_ming_without_models(self):
        class RootController(TGController):
            @expose()
            def test(self):

                return 'HI!'

        DBSession = scoped_session(sessionmaker(autoflush=True, autocommit=False))
        def init_model(engine):
            DBSession.configure(bind=engine)

        conf = AppConfig(minimal=True, root_controller=RootController())

        conf['use_ming'] = True
        conf['ming.url'] = 'mim://'
        app = conf.make_wsgi_app()

    def test_create(self):
        pass

    def test_setup_helpers_and_globals(self):
        self.config._setup_helpers_and_globals(self.config._init_config({}, {}))

    def test_setup_helpers_and_globals_custom_backward_compatible(self):
        def custom_helpers(conf):
            conf['helpers'] = 'YES!'

        object.__setattr__(self.config, '_setup_helpers_and_globals', custom_helpers)
        conf = self.config.make_load_environment()({}, {})
        assert conf['helpers'] == 'YES!', conf.get('helpers')

    def test_setup_sa_auth_backend(self):
        class ConfigWithSetupAuthBackend(self.config.__class__):
            called = []

            def setup_sa_auth_backend(self):
                self.called.append(True)

        conf = ConfigWithSetupAuthBackend()
        conf._setup_auth(conf._init_config({}, {}))

        assert len(ConfigWithSetupAuthBackend.called) >= 1

    def test_setup_sa_auth_custom_backward_compatible(self):
        class ConfigWithSetupAuthBackend(self.config.__class__):
            called = []

            def _setup_auth(self, app_config):
                self.called.append(True)

        conf = ConfigWithSetupAuthBackend()
        conf._setup_auth(conf._init_config({}, {}))

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
            def _add_tm_middleware(self, config, app):
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

        # Check the custom manager got configured
        assert conf.did_perform_custom_tm == True

        # The transaction manager wrapper should not have been enabled.
        tgapp = TGApp()
        wrapper = tgapp.wrapped_dispatch
        while wrapper != tgapp._dispatch:
            assert not isinstance(wrapper, TransactionApplicationWrapper)
            wrapper = wrapper.next_handler

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
        conf['tm.enabled'] = True
        conf['tm.commit_veto'] = custom_commit_veto
        conf['sqlalchemy.url'] = 'sqlite://'

        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert hasattr(conf, 'use_transaction_manager') is False

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
        conf['tm.enabled'] = True
        conf['sqlalchemy.url'] = 'sqlite://'

        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert hasattr(conf, 'use_transaction_manager') is False

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
        conf['tm.enabled'] = True
        conf['sqlalchemy.url'] = 'sqlite://'
        conf['tm.attempts'] = 3

        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert hasattr(conf, 'use_transaction_manager') is False

        resp = app.get('/test')
        assert 'HI' in resp

        transaction.manager = prev_transaction_manager

    def test_old_sqlalchemy_commit_veto(self):
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

    def test_old_sqlalchemy_doom(self):
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

    def test_old_sqlalchemy_retry(self):
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

    def test_old_sqlalchemy_is_disabled_when_missing(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = False
        conf.use_transaction_manager = True

        app = conf.make_wsgi_app()
        assert conf.use_transaction_manager is False

    def test_setup_persistence_custom_backward_compatible(self):
        self.config.package = PackageWithModel()

        def custom_persistence(conf):
            conf['gotcha'] = 'YES!'

        object.__setattr__(self.config, '_setup_persistence', custom_persistence)
        conf = self.config.make_load_environment()({}, {})
        assert conf['gotcha'] == 'YES!', conf

    def test_setup_sqla_persistance(self):
        self.config['sqlalchemy.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config._setup_persistence(self.config._init_config({}, {}))

    def test_setup_sqla_balanced(self):
        self.config['sqlalchemy.master.url'] = 'sqlite://'
        self.config['sqlalchemy.slaves.slave1.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config._setup_persistence(self.config._init_config({}, {}))

    @raises(TGConfigError)
    def test_setup_sqla_balanced_prevent_slave_named_master(self):
        self.config['sqlalchemy.master.url'] = 'sqlite://'
        self.config['sqlalchemy.slaves.master.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config._setup_persistence(self.config._init_config({}, {}))

    @raises(TGConfigError)
    def test_setup_sqla_balanced_no_slaves(self):
        self.config['sqlalchemy.master.url'] = 'sqlite://'
        self.config.use_sqlalchemy = True

        self.config.package = PackageWithModel()
        self.config._setup_persistence(self.config._init_config({}, {}))

    def test_setup_ming_persistance(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://'
        conf['ming.db'] = 'inmemdb'

        app = conf.make_wsgi_app()

        tgapp = app.application
        while not isinstance(tgapp, TGApp):
            tgapp = tgapp.app

        ming_handler = tgapp.wrapped_dispatch
        while ming_handler != tgapp._dispatch:
            if isinstance(ming_handler, MingApplicationWrapper):
                break
            ming_handler = ming_handler.next_handler
        assert isinstance(ming_handler, MingApplicationWrapper), ming_handler

        class FakeMingSession(object):
            actions = []

            def flush_all(self):
                self.actions.append('FLUSH')

            def close_all(self):
                self.actions.append('CLOSE')

        ming_handler.ThreadLocalODMSession = FakeMingSession()

        app = TestApp(app)
        resp = app.get('/test')
        assert 'HI' in resp

        assert ming_handler.ThreadLocalODMSession.actions == ['FLUSH']

    def test_setup_ming_persistance_closes_on_failure(self):
        class RootController(TGController):
            @expose()
            def test(self):
                raise Exception('CRASH!')

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://'
        conf['ming.db'] = 'inmemdb'

        app = conf.make_wsgi_app()

        tgapp = app.application
        while not isinstance(tgapp, TGApp):
            tgapp = tgapp.app

        ming_handler = tgapp.wrapped_dispatch
        while ming_handler != tgapp._dispatch:
            if isinstance(ming_handler, MingApplicationWrapper):
                break
            ming_handler = ming_handler.next_handler
        assert isinstance(ming_handler, MingApplicationWrapper), ming_handler

        class FakeMingSession(object):
            actions = []

            def flush_all(self):
                self.actions.append('FLUSH')

            def close_all(self):
                self.actions.append('CLOSE')

        ming_handler.ThreadLocalODMSession = FakeMingSession()

        app = TestApp(app)

        try:
            app.get('/test', status=500)
        except:
            assert ming_handler.ThreadLocalODMSession.actions == ['CLOSE']
        else:
            assert False, 'Should have raised exception'

    def test_setup_ming_persistance_with_url_alone(self):
        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://inmemdb'

        app = conf.make_wsgi_app()
        assert app is not None

        dstore = config['tg.app_globals'].ming_datastore
        dstore_name = dstore.name
        # Looks like ming has empty dstore.name when using MIM.
        assert dstore_name == '', dstore

    def test_setup_sqla_and_ming_both(self):
        package = PackageWithModel()
        base_config = AppConfig(minimal=True, root_controller=None)
        base_config.package = package
        base_config.model = package.model
        base_config.use_ming = True
        base_config['ming.url'] = 'mim://inmemdb'
        base_config.use_sqlalchemy = True
        base_config['sqlalchemy.url'] = 'sqlite://'

        app = base_config.make_wsgi_app()
        assert app is not None

        assert config['MingSession'], config
        assert config['tg.app_globals'].ming_datastore, config['tg.app_globals']

        assert config['SQLASession'], config
        assert config['tg.app_globals'].sa_engine, config['tg.app_globals']

        assert config['DBSession'] is config['SQLASession'], config

    def test_setup_ming_persistance_with_url_and_db(self):
        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://inmemdb'
        conf['ming.db'] = 'realinmemdb'

        app = conf.make_wsgi_app()
        assert app is not None

        dstore = config['tg.app_globals'].ming_datastore
        dstore_name = dstore.name
        assert dstore_name == 'realinmemdb', dstore

    def test_setup_ming_persistance_advanced_options(self):
        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mim://inmemdb'
        conf['ming.connection.read_preference'] = 'PRIMARY'

        app = conf.make_wsgi_app()
        assert app is not None

    def test_setup_ming_persistance_replica_set(self):
        if sys.version_info[:2] == (2, 6):
            raise SkipTest()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mongodb://localhost:27017,localhost:27018/testdb?replicaSet=test'
        conf['ming.db'] = ''

        app = conf.make_wsgi_app()
        assert app is not None

        expected_url = 'mongodb://localhost:27017,localhost:27018/?replicaSet=test'
        expected_db = 'testdb'

        dstore = config['tg.app_globals'].ming_datastore
        assert expected_db == dstore.name, dstore.name
        assert expected_url == dstore.bind._conn_args[0], dstore.bind._conn_args

    def test_setup_mig_persistance_replica_set_option(self):
        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mongodb://localhost:27017,localhost:27018/testdb'
        conf['ming.connection.replicaSet'] = 'test'
        conf['ming.db'] = ''

        app = conf.make_wsgi_app()
        assert app is not None

        expected_url = 'mongodb://localhost:27017,localhost:27018/'
        expected_db = 'testdb'

        dstore = config['tg.app_globals'].ming_datastore
        assert expected_db == dstore.name, dstore.name
        assert expected_url == dstore.bind._conn_args[0], dstore.bind._conn_args
        assert 'test' == dstore.bind._conn_kwargs.get('replicaSet'), dstore.bind._conn_kwargs

    def test_add_auth_middleware(self):
        class Dummy:pass

        self.config.sa_auth.dbsession = Dummy()
        self.config.sa_auth.user_class = Dummy
        self.config.sa_auth.group_class = Dummy
        self.config.sa_auth.permission_class = Dummy
        self.config.sa_auth.cookie_secret = 'dummy'
        self.config.sa_auth.password_encryption_method = 'sha'

        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

    def test_add_static_file_middleware(self):
        self.config._add_static_file_middleware(self.config._init_config({}, {}), None)

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
        conf.use_sqlalchemy = True
        conf.auth_backend = 'sqlalchemy'
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                           'dbsession': None,
                           'user_class': None,
                           'cookie_secret': '12345'}
        conf['sqlalchemy.url'] = 'sqlite://'
        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        assert 'repoze.who.plugins' in resp, resp

        self.config.auth_backend = None

    def test_setup_ming_auth(self):
        self.config.auth_backend = 'ming'

        self.config._setup_auth(self.config._init_config({}, {}))
        assert 'sa_auth' in config

        self.config.auth_backend = None

    def test_deprecated_register_hooks(self):
        def dummy(*args):
            pass

        milestones.config_ready._reset()
        milestones.environment_loaded._reset()

        self.config.register_hook('startup', dummy)
        self.config.register_hook('shutdown', dummy)
        self.config.register_hook('controller_wrapper', dummy)
        for hook_name in ('before_validate', 'before_call', 'before_render',
                          'after_render', 'before_render_call', 'after_render_call',
                          'before_config', 'after_config'):
            self.config.register_hook(hook_name, dummy)

        milestones.config_ready.reach()
        milestones.environment_loaded.reach()

        for hooks in ('before_validate', 'before_call', 'before_render',
                      'after_render', 'before_render_call', 'after_render_call',
                      'before_config', 'after_config', 'startup', 'shutdown'):
            assert tg.hooks._hooks[hooks]

        assert self.config.controller_wrappers

    @raises(TGConfigError)
    def test_missing_secret(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config.pop('session.secret', None)
        self.config._setup_auth(self.config._init_config({}, {}))

    def test_sessions_enabled(self):
        class RootController(TGController):
            @expose('json')
            def test(self):
                try:
                    tg.session['counter'] += 1
                except KeyError:
                    tg.session['counter'] = 0

                tg.session.save()
                return dict(counter=tg.session['counter'])

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['session.enabled'] = True
        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        assert resp.json['counter'] == 0, resp

        resp = app.get('/test')
        assert resp.json['counter'] == 1, resp

    def test_backware_compatible_sessions_enabled(self):
        class RootController(TGController):
            @expose('json')
            def test(self):
                try:
                    tg.session['counter'] += 1
                except KeyError:
                    tg.session['counter'] = 0

                tg.session.save()
                return dict(counter=tg.session['counter'])

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['session.enabled'] = False
        conf['use_session_middleware'] = True
        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        assert resp.json['counter'] == 0, resp

        resp = app.get('/test')
        assert resp.json['counter'] == 1, resp

    def test_caching_enabled(self):
        class RootController(TGController):
            @expose('json')
            def test(self):
                cache = tg.cache.get_cache('test_caching_enabled')
                now = cache.get_value('test_cache_key', createfunc=datetime.utcnow)
                return dict(now=now)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['cache.enabled'] = True
        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        now = resp.json['now']

        for x in range(20):
            resp = app.get('/test')
            assert resp.json['now'] == now, (resp, now)

    def test_backward_compatible_caching_enabled(self):
        class RootController(TGController):
            @expose('json')
            def test(self):
                cache = tg.cache.get_cache('test_caching_enabled')
                now = cache.get_value('test_cache_key', createfunc=datetime.utcnow)
                return dict(now=now)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['cache.enabled'] = False
        conf['use_cache_middleware'] = True
        app = conf.make_wsgi_app()
        app = TestApp(app)

        resp = app.get('/test')
        now = resp.json['now']

        for x in range(20):
            resp = app.get('/test')
            assert resp.json['now'] == now, (resp, now)

    def test_controler_wrapper_setup(self):
        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = []
        self.config._setup_controller_wrappers(self.config._init_config({}, {}))
        assert config['controller_caller'] == orig_caller

        def controller_wrapper(caller):
            def call(*args, **kw):
                return caller(*args, **kw)
            return call

        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = [controller_wrapper]
        self.config._setup_controller_wrappers(self.config._init_config({}, {}))
        assert config['controller_caller'].__name__ == controller_wrapper(orig_caller).__name__

    def test_backward_compatible_controler_wrapper_setup(self):
        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = []
        self.config._setup_controller_wrappers(self.config._init_config({}, {}))
        assert config['controller_caller'] == orig_caller

        def controller_wrapper(app_config, caller):
            def call(*args, **kw):
                return caller(*args, **kw)
            return call

        orig_caller = self.config.controller_caller
        self.config.controller_wrappers = [controller_wrapper]
        self.config._setup_controller_wrappers(self.config._init_config({}, {}))

        deprecated_wrapper = config['controller_caller'].wrapper
        assert deprecated_wrapper.__name__ == controller_wrapper(self.config, orig_caller).__name__

    def test_global_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
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

    def test_backward_compatible_global_controller_wrapper(self):
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

        def controller_wrapper2(app_config, caller):
            def call(controller, remainder, params):
                wrapper_has_been_visited.append(True)
                return caller(controller, remainder, params)
            return call

        def controller_wrapper3(caller):
            def call(config, controller, remainder, params):
                wrapper_has_been_visited.append(True)
                return caller(config, controller, remainder, params)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_hook('controller_wrapper', controller_wrapper2)
        conf.register_hook('controller_wrapper', controller_wrapper3)
        conf.register_hook('controller_wrapper', controller_wrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert len(wrapper_has_been_visited) == 3

    def test_dedicated_controller_wrapper(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_controller_wrapper(controller_wrapper, controller=RootController.test)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True

    def test_dedicated_controller_wrapper_old(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
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
        def app_controller_wrapper(caller):
            def call(*args, **kw):
                app_wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
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

    def test_controler_wrapper_after_environment_setup(self):
        milestones._reset_all()

        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        wrapper_has_been_visited = []
        def controller_wrapper(caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_controller_wrapper(controller_wrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True
        assert len(wrapper_has_been_visited) == 1

        conf.register_controller_wrapper(controller_wrapper)
        app2 = conf.make_wsgi_app()
        app2 = TestApp(app2)

        wrapper_has_been_visited[:] = []
        assert 'HI!' in app2.get('/test')
        assert wrapper_has_been_visited[0] is True
        assert len(wrapper_has_been_visited) == 2

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

        app_wrappers = list(conf.application_wrappers.values())
        assert app_wrappers[0] == AppWrapper1
        assert app_wrappers[1] == AppWrapper2
        assert app_wrappers[2] == AppWrapper3
        assert app_wrappers[3] == AppWrapper4
        assert app_wrappers[4] == AppWrapper5

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
            self.config._setup_renderers(self.config._init_config({}, {}))
        except TGConfigError:
            self.config.renderers = renderers
        else:
            assert False

    @raises(TGConfigError)
    def test_cookie_secret_required(self):
        self.config.sa_auth = {}
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

    def test_sqla_auth_middleware(self):
        if PY3: raise SkipTest()

        self.config.auth_backend = 'sqlalchemy'
        self.config.skip_authentication = True
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadata(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])}
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

        authenticators = [x[0] for x in cfg['sa_auth']['authenticators']]
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
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

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

        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

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
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

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
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

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
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

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
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

        authenticators = [x[0] for x in self.config['sa_auth']['authenticators']]
        assert 'cookie' in authenticators
        assert 'tgappauth' in authenticators

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_auth_setup_default_identifier(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'identifiers': UncopiableList([('default', None)])}
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

        identifiers = [x[0] for x in self.config['sa_auth']['identifiers']]
        assert 'cookie' in identifiers

        self.config['sa_auth'] = {}
        self.config.auth_backend = None

    def test_auth_setup_custom_identifier(self):
        self.config.auth_backend = 'sqlalchemy'
        self.config['sa_auth'] = {'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'identifiers': UncopiableList([('custom', None)])}
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

        identifiers = [x[0] for x in self.config['sa_auth']['identifiers']]
        assert 'custom' in identifiers

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
        cfg = self.config._init_config({}, {})
        self.config._setup_auth(cfg)
        self.config._add_auth_middleware(cfg, None)

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
        self.config._add_tosca_middleware(config, None)
        config.pop('toscawidgets.framework.resource_variant', None)

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
        class RootController(TGController):
            pass

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'DONE' in app.get('/_test_vars')
        assert request.path == '/_test_vars'

        # This should trash away the preserved registry to avoid
        # leaking memory.
        app.get('/', status=404)

        try:
            request.path
        except TypeError:
            # TypeError means the request has been properly removed
            pass
        else:
            assert False, 'There should have been no requests in place...'

    def test_application_empty_controller(self):
        class RootController(object):
            def __call__(self, environ, start_response):
                return None

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        try:
            r = app.get('/something')
        except Exception as e:
            assert 'No content returned by controller' in str(e)
        else:
            assert False, 'Should have raised "No content returned by controller"'

    def test_application_test_mode_detection(self):
        class FakeRegistry(object):
            def register(self, *args, **kw):
                pass

        a = TGApp()
        testmode, __, __ = a._setup_app_env({'paste.registry':FakeRegistry()})
        assert testmode is False

        testmode, __, __ = a._setup_app_env({'paste.registry':FakeRegistry(),
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
        conf.register_wrapper(AppWrapper)
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
        conf['errorpage.enabled'] = True
        conf['errorpage.handle_exceptions'] = False
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
        conf['errorpage.enabled'] = True
        conf['errorpage.handle_exceptions'] = False
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' in resp, resp

    def test_error_document_passthrough(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                request.disable_error_pages()
                abort(403, detail='Custom Detail')

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['errorpage.enabled'] = True
        conf['errorpage.handle_exceptions'] = False
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'Custom Detail' in resp, resp

    def test_custom_old_error_document(self):
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
        conf['errorpage.enabled'] = True
        conf.status_code_redirect = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' in resp, resp

    def test_custom_old_error_document_with_streamed_response(self):
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
        conf['errorpage.enabled'] = True
        conf.status_code_redirect = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' in resp, resp

    def test_custom_500_document(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                abort(500)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['errorpage.enabled'] = True
        conf['debug'] = False
        conf['errorpage.handle_exceptions'] = False
        conf['errorpage.status_codes'] += [500]
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=500)
        assert 'ERROR!!!' in resp, resp

    def test_custom_500_document_on_crash(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                raise Exception('Crash!')

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['errorpage.enabled'] = True
        conf['debug'] = False
        conf['errorpage.handle_exceptions'] = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=500)
        assert 'ERROR!!!' in resp, resp

    def test_errorpage_reraises_exceptions(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                raise Exception('Crash!')

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['errorpage.enabled'] = True
        conf['debug'] = False
        conf['errorpage.handle_exceptions'] = False
        app = conf.make_wsgi_app(full_stack=False)
        app = TestApp(app)

        try:
            resp = app.get('/test', status=500)
        except Exception as e:
            assert 'Crash!' in str(e)
        else:
            assert False, 'Should have raised Crash! exception'

    def test_old_custom_500_document(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                abort(500)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['debug'] = False
        conf.status_code_redirect = True
        conf['errorpage.enabled'] = True
        conf['errorpage.status_codes'] += [500]
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=500)
        assert 'ERROR!!!' in resp, resp

    def test_skips_custom_500_document_when_debug(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                abort(500)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['errorpage.enabled'] = True
        conf['debug'] = True
        conf['errorpage.handle_exceptions'] = False
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=500)
        assert 'ERROR!!!' not in resp, resp

    def test_skips_old_custom_500_document_when_debug(self):
        class ErrorController(TGController):
            @expose()
            def document(self, *args, **kw):
                return 'ERROR!!!'

        class RootController(TGController):
            error = ErrorController()
            @expose()
            def test(self):
                abort(500)

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['debug'] = True
        conf.status_code_redirect = True
        conf['errorpage.enabled'] = True
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=500)
        assert 'ERROR!!!' not in resp, resp

    def test_skips_custom_error_document_when_disabled(self):
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
        conf['errorpage.enabled'] = False
        conf['errorpage.status_codes'] = (403, 404)
        conf['errorpage.handle_exceptions'] = False
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' not in resp, resp

    def test_skips_custom_error_document_when_disabled_and_manually_registered(self):
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
        conf.register_wrapper(ErrorPageApplicationWrapper)
        conf['errorpage.enabled'] = False
        conf['errorpage.status_codes'] = (403, 404)
        conf['errorpage.handle_exceptions'] = False
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' not in resp, resp

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
        conf.renderers = ['json', 'genshi']
        conf.default_renderer = 'json'

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
        conf.renderers = ['json']
        conf.default_renderer = 'json'

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

    def test_make_body_seekable(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                request.body_file.seek(0)
                return 'HELLO'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['make_body_seekable'] = True

        app = conf.make_wsgi_app(full_stack=False)
        assert app.application.__class__.__name__ == 'SeekableRequestBodyMiddleware', \
            app.application.__class__

        app = TestApp(app)
        assert 'HELLO' in app.get('/test')

    def test_make_body_seekable_disabled(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                request.body_file.seek(0)
                return 'HELLO'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['make_body_seekable'] = False

        app = conf.make_wsgi_app(full_stack=False)
        app = TestApp(app)
        assert 'HELLO' in app.get('/test')

    def test_debug_middleware(self):
        class RootController(TGController):
            @expose()
            def test(self):
                raise Exception('Crash!')

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['errorpage.enabled'] = True
        app = conf.make_wsgi_app(global_conf={'debug': True}, full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=500)
        assert 'Exception: Crash! // Backlash' in resp, resp

    def test_make_app_with_custom_appglobals(self):
        class RootController(TGController):
            @expose('')
            def test(self, *args, **kwargs):
                return tg.app_globals.TEXT

        class FakeGlobals(Bunch):
            def __init__(self):
                super(FakeGlobals, self).__init__()
                self['TEXT'] = 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.app_globals = FakeGlobals
        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    def test_make_app_with_appglobals_submodule(self):
        class RootController(TGController):
            @expose('')
            def test(self, *args, **kwargs):
                return tg.app_globals.text

        conf = AppConfig(minimal=True, root_controller=RootController())

        from .fixtures import package_with_helpers_submodule
        conf['package'] = package_with_helpers_submodule
        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!!' in app.get('/test')

    def test_make_app_with_custom_helpers(self):
        class RootController(TGController):
            @expose('')
            def test(self, *args, **kwargs):
                return config['helpers'].get_text()

        class FakeHelpers(Bunch):
            @classmethod
            def get_text(cls):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.helpers = FakeHelpers()
        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    def test_make_app_with_helpers_submodule(self):
        class RootController(TGController):
            @expose('')
            def test(self, *args, **kwargs):
                return config['helpers'].get_text()

        conf = AppConfig(minimal=True, root_controller=RootController())

        from .fixtures import package_with_helpers_submodule
        conf['package'] = package_with_helpers_submodule
        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!!' in app.get('/test')

    def test_make_app_without_load_environment(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'Helpers: %s' % tg.config.get('helpers')

        conf = AppConfig(minimal=True, root_controller=RootController())
        cfg = conf._init_config({}, {})  # Manually call init_config otherwise no tg.config is pushed.
        app = conf.setup_tg_wsgi_app(load_environment=None)()
        app = TestApp(app)

        resp = app.get('/test')
        assert resp.text == 'Helpers: None', resp