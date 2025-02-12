"""
Testing for TG2 Configuration
"""
import os
import sys

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

try:
    import ming
except ImportError:
    # Ming is not supported on Python 3.8 
    ming = None
else:
    import ming.odm

from webtest import TestApp

import tg.i18n
from tests.base import setup_session_dir, teardown_session_dir, utcnow
from tg import (
    MinimalApplicationConfigurator,
    TGController,
    abort,
    expose,
    request,
    response,
)
from tg.appwrappers.mingflush import MingApplicationWrapper
from tg.configuration import config, milestones
from tg.configuration.app_config import AppConfig
from tg.configuration.auth import _AuthenticationForgerPlugin
from tg.configuration.auth.metadata import _AuthMetadataAuthenticator
from tg.configuration.tgconfig import _init_default_global_config
from tg.configuration.utils import TGConfigError, coerce_config, coerce_options
from tg.configurator import ApplicationConfigurator, FullStackApplicationConfigurator
from tg.configurator.base import (
    BeforeConfigConfigurationAction,
    ConfigurationComponent,
    Configurator,
)
from tg.configurator.components.app_globals import AppGlobalsConfigurationComponent
from tg.configurator.components.auth import SimpleAuthenticationConfigurationComponent
from tg.configurator.components.caching import CachingConfigurationComponent
from tg.configurator.components.dispatch import DispatchConfigurationComponent
from tg.configurator.components.helpers import HelpersConfigurationComponent
from tg.configurator.components.i18n import I18NConfigurationComponent
from tg.configurator.components.ming import MingConfigurationComponent
from tg.configurator.components.paths import PathsConfigurationComponent
from tg.configurator.components.registry import RegistryConfigurationComponent
from tg.configurator.components.rendering import TemplateRenderingConfigurationComponent
from tg.configurator.components.session import SessionConfigurationComponent
from tg.configurator.components.sqlalchemy import SQLAlchemyConfigurationComponent
from tg.configurator.components.transactions import (
    TransactionManagerConfigurationComponent,
)
from tg.renderers.base import RendererFactory
from tg.support.converters import asbool, asint
from tg.util import Bunch
from tg.wsgiapp import TGApp


def setup_module():
    milestones._reset_all()
    setup_session_dir()


def teardown_module():
    milestones._reset_all()
    teardown_session_dir()


def _reset_global_config():
    milestones._reset_all()
    try:
        config.config_proxy.pop_thread_config()
    except:
        pass
    try:
        config.config_proxy.pop_process_config()
    except:
        pass


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


class RootController(TGController):
    @expose()
    def test(self):
        return 'HI!'


class TestPylonsConfigWrapper:

    def setup_method(self):
        _reset_global_config()
        _init_default_global_config()
        self.config = config

    def teardown_method(self):
        _reset_global_config()
        _init_default_global_config()

    def test_create(self):
        pass

    def test_getitem(self):
        expected_keys = ['debug', 'package', 'tg.app_globals', 'tg.strict_tmpl_context']
        for key in expected_keys:
            self.config[key]

    def test_repr(self):
        _reset_global_config()
        assert repr(self.config) == '<TGConfig: missing>'
        _init_default_global_config()
        assert repr(self.config) == repr(self.config.config_proxy.current_conf())

    def test_getitem_bad(self):
        with pytest.raises(KeyError):
            self.config['no_such_key']

    def test_setitem(self):
        self.config['no_such_key'] = 'something'

    def test_delattr(self):
        del self.config.debug
        assert hasattr(self.config, 'debug') == False
        self.config.debug = False

    def test_delattr_bad(self):
        with pytest.raises(AttributeError):
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


class TestConfigurator:
    def setup_method(self):
        _reset_global_config()

    def teardown_method(self):
        _reset_global_config()
        tg.hooks._clear()  # Reset hooks

    def test_repr_action(self):
        act = BeforeConfigConfigurationAction()
        assert repr(act) == "<BeforeConfigConfigurationAction: None>"

    def test_reqlocal_configuration_dictionary(self):
        cfg = FullStackApplicationConfigurator()

        cfg.update_blueprint({'RANDOM_VALUE': 5})
        conf = cfg.configure({}, {})

        assert config['RANDOM_VALUE'] == 5
        assert len(config) == len(conf)

    def test_blueprint_invalid_view(self):
        cfg = FullStackApplicationConfigurator()
        try:
            cfg.get_blueprint_view('this.that.')
        except ValueError as e:
            assert str(e) == 'A Blueprint key cannot end with a .'
        else:
            assert False, 'Should have raised'

    def test_invalid_component(self):
        cfg = FullStackApplicationConfigurator()
        try:
            cfg.register(str)
        except ValueError as e:
            assert str(e) == 'Configuration component must inherit ConfigurationComponent'
        else:
            assert False, 'Should have raised'

    def test_replace_component(self):
        cfg = FullStackApplicationConfigurator()

        class TestComponentFirst(ConfigurationComponent):
            id = 'TESTCOMPONENT'

        class TestComponentSecond(ConfigurationComponent):
            id = 'TESTCOMPONENT2'

        cfg.register(TestComponentFirst)
        try:
            cfg.replace(TestComponentFirst, str)
        except ValueError as e:
            assert str(e) == 'Configuration component must inherit ConfigurationComponent'
        else:
            assert False, 'Should have raised'

        cfg.replace('TESTCOMPONENT', TestComponentSecond)
        comp = cfg.get_component('TESTCOMPONENT')
        assert isinstance(comp, TestComponentSecond), comp

    def test_component_without_id(self):
        cfg = FullStackApplicationConfigurator()

        class TestComponentFirst(ConfigurationComponent):
            pass

        try:
            cfg.register(TestComponentFirst)
        except ValueError as e:
            assert str(e).startswith('ConfigurationComponent must provide an id class attribute')
        else:
            assert False, 'Should have raised'

        try:
            cfg.replace(TestComponentFirst, TestComponentFirst)
        except ValueError as e:
            assert str(e).startswith('ConfigurationComponent must provide an id class attribute')
        else:
            assert False, 'Should have raised'

    def test_retrieve_current_configurator(self):
        cfg = FullStackApplicationConfigurator()
        cfg.update_blueprint({'RANDOM_VALUE': 5})
        cfg.configure({}, {})

        configurator = FullStackApplicationConfigurator.current()
        assert configurator.get_blueprint_value('RANDOM_VALUE') == 5

    def test_application_wrapper_replacement(self):
        class AppWrapperTest(object):
            def __init__(self, *args, **kwargs): pass
            def __call__(self, *args, **kw):
                return tg.Response('AppWrapper #1')

        class AppWrapperTestReplacement(object):
            def __init__(self, *args, **kwargs): pass
            def __call__(self, *args, **kw):
                return tg.Response('AppWrapper #2')

        cfg = FullStackApplicationConfigurator()
        cfg.update_blueprint({'root_controller': Bunch(index=lambda *args, **kwargs: 'HI')})
        cfg.register_application_wrapper(AppWrapperTest)

        app = TestApp(cfg.make_wsgi_app({'debug': True}, {}))
        assert app.get('/').text == 'AppWrapper #1', app.get('/').text

        cfg.replace_application_wrapper('AppWrapperTest', AppWrapperTestReplacement)

        app = TestApp(cfg.make_wsgi_app({}, {}))
        assert app.get('/').text == 'AppWrapper #2', app.get('/').text

    def test_sa_auth_requires_app_config(self):
        configurator = Configurator()
        configurator.register(SimpleAuthenticationConfigurationComponent)

        try:
            configurator.configure({}, {})
        except TGConfigError as e:
            assert str(e) == 'Simple Authentication only works on an ApplicationConfigurator'
        else:
            assert False, 'Should have raised'

    def test_sa_auth_authmetadata_without_authenticate(self):
        cfg = FullStackApplicationConfigurator()
        class FakeAuthMetadata():
            authenticate = None
        cfg.update_blueprint({
            'root_controller': Bunch(index=lambda *args, **kwargs: 'HI'),
            'sa_auth.enabled': True,
            'sa_auth.authmetadata': FakeAuthMetadata(),
            'sa_auth.cookie_secret': 'SECRET!'
        })
        cfg.make_wsgi_app({}, {})

    def test_caching_required_app_config(self):
        configurator = Configurator()
        configurator.register(CachingConfigurationComponent)

        try:
            configurator.configure({}, {})
        except TGConfigError as e:
            assert str(e) == 'Caching only works on an ApplicationConfigurator'
        else:
            assert False, 'Should have raised'

    def test_i18n_required_app_config(self):
        configurator = Configurator()
        configurator.register(I18NConfigurationComponent)

        try:
            configurator.configure({}, {})
        except TGConfigError as e:
            assert str(e) == 'I18N only works on an ApplicationConfigurator'
        else:
            assert False, 'Should have raised'

    def test_ming_required_app_config(self):
        configurator = Configurator()
        configurator.register(MingConfigurationComponent)

        try:
            configurator.configure({}, {})
        except TGConfigError as e:
            assert str(e).endswith('only works on an ApplicationConfigurator')
        else:
            assert False, 'Should have raised'

    def test_session_required_app_config(self):
        configurator = Configurator()
        configurator.register(SessionConfigurationComponent)

        try:
            configurator.configure({}, {})
        except TGConfigError as e:
            assert str(e).endswith('only work on an ApplicationConfigurator')
        else:
            assert False, 'Should have raised'

    def test_sqlalchemy_required_app_config(self):
        configurator = Configurator()
        configurator.register(SQLAlchemyConfigurationComponent)

        try:
            configurator.configure({}, {})
        except TGConfigError as e:
            assert str(e).endswith('only works on an ApplicationConfigurator')
        else:
            assert False, 'Should have raised'

    def test_transaction_required_app_config(self):
        configurator = Configurator()
        configurator.register(TransactionManagerConfigurationComponent)

        try:
            configurator.configure({}, {})
        except TGConfigError as e:
            assert str(e).endswith('only works on an ApplicationConfigurator')
        else:
            assert False, 'Should have raised'

    def test_dispatch_without_mimetypes(self):
        # This is exactly like MinimalApplicationConfigurator
        # but without the mimetypes component.
        apc = ApplicationConfigurator()
        apc.register(PathsConfigurationComponent, after=False)
        apc.register(DispatchConfigurationComponent, after=False)
        apc.register(AppGlobalsConfigurationComponent)
        apc.register(HelpersConfigurationComponent)
        apc.register(TemplateRenderingConfigurationComponent)
        apc.register(RegistryConfigurationComponent, after=True)

        class MinimalController(TGController):
            @expose()
            def index(self):
                return 'HI'

        apc.update_blueprint({
            'root_controller': MinimalController()
        })
        app = TestApp(apc.make_wsgi_app({}, {}))
        assert app.get('/').text == 'HI'

    def test_app_without_controller(self):
        cfg = MinimalApplicationConfigurator()
        app = TestApp(cfg.make_wsgi_app({}, {}))

        try:
            app.get('/')
        except TGConfigError as e:
            assert str(e) == 'Unable to load controllers, no controllers path configured!'
        else:
            assert False, 'Should have raised.'

    def test_tgapp_caches_controller_classes(self):
        class RootController(TGController):
            @expose()
            def index(self):
                return 'HI'

        tgapp = Bunch(app=None)
        def save_app(app):
            tgapp.app = app
            return app

        cfg = MinimalApplicationConfigurator()
        app = TestApp(cfg.make_wsgi_app({}, {}, wrap_app=save_app))

        tgapp.app.controller_classes['root'] = RootController
        assert app.get('/').text == 'HI'


class TestAppConfig:
    def setup_method(self):
        _reset_global_config()
        self.fake_package = PackageWithModel

    def teardown_method(self):
        _reset_global_config()
        tg.hooks._clear()  # Reset hooks

    def test_get_value(self):
        conf = AppConfig(minimal=True)
        conf['existing_value'] = 5
        assert conf['existing_value'] == 5
        assert conf.get('non_existing_value') == None

    def test_missing_attribute(self):
        conf = AppConfig(minimal=True)
        conf['existing_value'] = 5
        assert conf['existing_value'] == 5
        assert conf.existing_value == 5

        try:
            conf['missing_value']
        except KeyError:
            pass
        else:
            raise RuntimeError('Should have raised KeyError')

        try:
            conf.missing_value
        except AttributeError:
            pass
        else:
            raise RuntimeError('Should have raised AttributeError')

    def test_lang_can_be_changed_by_ini(self):
        conf = AppConfig(minimal=True)
        conf.make_wsgi_app(**{'i18n.lang': 'ru'})
        assert config['i18n.lang'] == 'ru'

    def test_create_minimal_app(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    def test_create_minimal_app_with_factory(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        app_factory = conf.setup_tg_wsgi_app()
        app = app_factory()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

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

    def test_sqlalchemy_without_models(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['use_sqlalchemy'] = True
        conf['sqlalchemy.url'] = 'sqlite://'

        with pytest.raises(TGConfigError):
            app = conf.make_wsgi_app()

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
    def test_minimal_app_with_ming(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return 'HI!'

        mainsession = ming.Session()
        DBSession = ming.odm.ThreadLocalORMSession(mainsession)

        def init_model(engine):
            mainsession.bind = engine

        conf = AppConfig(minimal=True, root_controller=RootController())

        conf['use_ming'] = True
        conf['ming.url'] = 'mim:///dbname'
        conf['model'] = Bunch(init_model=init_model, DBSession=DBSession)

        app = conf.make_wsgi_app()
        app = TestApp(app)
        assert 'HI!' in app.get('/test')

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
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

        with pytest.raises(TGConfigError):
            app = conf.make_wsgi_app()

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
        conf['package'] = package
        conf['model'] = package.model
        conf['use_sqlalchemy'] = True
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

    def test_setup_sqla_persistance(self):
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['sqlalchemy.url'] = 'sqlite://'
        conf.use_sqlalchemy = True
        conf.package = PackageWithModel()

        conf.make_wsgi_app()

    def test_setup_sqla_balanced(self):
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['sqlalchemy.master.url'] = 'sqlite://'
        conf['sqlalchemy.slaves.slave1.url'] = 'sqlite://'
        conf.use_sqlalchemy = True
        conf.package = PackageWithModel()

        conf.make_wsgi_app()

    def test_setup_sqla_balanced_prevent_slave_named_master(self):
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['sqlalchemy.master.url'] = 'sqlite://'
        conf['sqlalchemy.slaves.master.url'] = 'sqlite://'
        conf.use_sqlalchemy = True
        conf.package = PackageWithModel()

        with pytest.raises(TGConfigError):
            conf.make_wsgi_app()

    def test_setup_sqla_balanced_no_slaves(self):
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf['sqlalchemy.master.url'] = 'sqlite://'
        conf.use_sqlalchemy = True
        conf.package = PackageWithModel()

        with pytest.raises(TGConfigError):
            conf.make_wsgi_app()

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
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

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
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

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
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

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
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

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
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

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
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

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
    def test_setup_ming_persistance_replica_set(self):
        if sys.version_info[:2] == (2, 6):
            pytest.skip()

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mongodb://localhost:27017,localhost:27018/testdb?replicaSet=test'
        conf['ming.db'] = ''

        app = conf.make_wsgi_app()
        assert app is not None

        expected_url = 'mongodb://localhost:27017,localhost:27018/testdb?replicaSet=test'
        expected_db = 'testdb'

        dstore = config['tg.app_globals'].ming_datastore
        assert expected_db == dstore.name, dstore.name
        assert dstore.bind._conn_args[0] == expected_url

    @pytest.mark.skipif(ming is None, reason="Ming not supported on this system")
    def test_setup_ming_persistance_replica_set_option(self):
        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_ming = True
        conf['ming.url'] = 'mongodb://localhost:27017,localhost:27018/testdb'
        conf['ming.connection.replicaSet'] = 'test'

        app = conf.make_wsgi_app()
        assert app is not None

        expected_url = 'mongodb://localhost:27017,localhost:27018/testdb'
        expected_db = 'testdb'

        dstore = config['tg.app_globals'].ming_datastore
        assert expected_db == dstore.name, dstore.name
        assert dstore.bind._conn_args[0] == expected_url
        assert 'test' == dstore.bind._conn_kwargs.get('replicaSet'), dstore.bind._conn_kwargs

    def test_setup_authtkt(self):
        class RootController(TGController):
            @expose()
            def test(self):
                return str(request.environ)

        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf["sa_auth.enabled"] = True
        conf['sa_auth'] = {'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                           'dbsession': None,
                           'user_class': None,
                           'cookie_secret': '12345',
                           'post_login_url': '/'}
        conf['sqlalchemy.url'] = 'sqlite://'

        secure_app = conf.make_wsgi_app(**{'sa_auth.authtkt.secure': True})
        secure_app = TestApp(secure_app)
        resp = secure_app.post('/login_handler', params={'login': 'l', 'password': 'p'})
        assert 'HttpOnly' in resp.headers["Set-Cookie"], resp.headers

        insecure_app = conf.make_wsgi_app(**{'sa_auth.authtkt.secure': False})
        insecure_app = TestApp(insecure_app)
        resp = insecure_app.post('/login_handler', params={'login': 'l', 'password': 'p'})
        assert 'HttpOnly' not in resp.headers["Set-Cookie"], resp.headers


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

    def test_caching_enabled(self):
        class RootController(TGController):
            @expose('json')
            def test(self):
                cache = tg.cache.get_cache('test_caching_enabled')
                now = cache.get_value('test_cache_key', createfunc=utcnow)
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

    def test_controler_wrapper_setup(self):
        from tg.configurator.components.dispatch import _call_controller
        orig_caller = _call_controller

        appcfg = AppConfig(minimal=True, root_controller=RootController())

        conf = {}
        dispatch = appcfg._configurator.get_component('dispatch')
        dispatch._controller_wrappers[:] = []
        dispatch._setup_controller_wrappers(conf, None)
        assert conf['controller_caller'] == orig_caller

        def controller_wrapper(caller):
            def call(*args, **kw):
                return caller(*args, **kw)
            return call

        conf = {}
        dispatch = appcfg._configurator.get_component('dispatch')
        dispatch._controller_wrappers[:] = [controller_wrapper]
        dispatch._setup_controller_wrappers(conf, None)
        assert conf['controller_caller'].__name__ == controller_wrapper(orig_caller).__name__

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
        conf.register_controller_wrapper(controller_wrapper)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert wrapper_has_been_visited[0] is True

    def test_multiple_global_controller_wrapper(self):
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

        def controller_wrapper2(caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        def controller_wrapper3(caller):
            def call(*args, **kw):
                wrapper_has_been_visited.append(True)
                return caller(*args, **kw)
            return call

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_controller_wrapper(controller_wrapper2)
        conf.register_controller_wrapper(controller_wrapper3)
        conf.register_controller_wrapper(controller_wrapper)
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
        conf.register_controller_wrapper(controller_wrapper, controller=RootController.test)
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
        conf.register_controller_wrapper(app_controller_wrapper)
        conf.register_controller_wrapper(controller_wrapper, controller=RootController.test)
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

        app_wrappers = list(conf._configurator._application_wrappers.values())
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
        conf = AppConfig(root_controller=RootController())
        conf['renderers'] = ['unknwon']

        try:
            conf.make_wsgi_app()
        except TGConfigError as e:
            assert 'This configuration object does not support the unknwon renderer' in str(e)
        else:
            assert False

    def test_cookie_secret_required(self):
        conf = AppConfig(root_controller=RootController())
        conf['sa_auth.enabled'] = True
        conf['sa_auth'] = {}
        try:
            conf.make_wsgi_app()
        except TGConfigError as e:
            assert str(e).startswith('You must provide a value for authentication cookies secret')
        else:
            assert False

    def test_sqla_auth_middleware_only_mine(self):
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
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'

        conf["sa_auth.enabled"] = True
        alwaysadmin = _AuthenticationForgerPlugin(fake_user_key='FAKE_USER')
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadata(),
                           'cookie_secret':'12345',
                           'form_plugin':alwaysadmin,
                           'authenticators':UncopiableList([('alwaysadmin', alwaysadmin)]),
                           'identifiers':[('alwaysadmin', alwaysadmin)],
                           'challengers':[]})

        app = conf.make_wsgi_app()

        authenticators = [x[0] for x in config['sa_auth.authenticators']]
        assert authenticators[0] == 'alwaysadmin'
        assert 'sqlauth' not in authenticators

        challengers = [x[1] for x in config['sa_auth.challengers']]
        assert alwaysadmin in challengers

        app = TestApp(app)
        assert 'repoze.who.identity' in app.get('/test', extra_environ={'FAKE_USER':'admin'})
        assert app.get('/forbidden', status=401)

    def test_sqla_auth_logging_stderr(self):
        package = PackageWithModel()
        conf = AppConfig(minimal=True, root_controller=None)
        conf.package = package
        conf.model = package.model
        conf.use_sqlalchemy = True
        conf['sqlalchemy.url'] = 'sqlite://'

        conf["sa_auth.enabled"] = True
        alwaysadmin = _AuthenticationForgerPlugin(fake_user_key='FAKE_USER')
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadata(),
                                'cookie_secret':'12345',
                                'form_plugin':alwaysadmin,
                                'log_level':'DEBUG',
                                'authenticators':UncopiableList([('alwaysadmin', alwaysadmin)]),
                                'identifiers':[('alwaysadmin', alwaysadmin)],
                                'challengers':[]})

        conf['sa_auth']['log_file'] = 'stderr'
        app = conf.make_wsgi_app()
        conf['sa_auth']['log_file'] = 'stdout'
        app = conf.make_wsgi_app()

        import tempfile
        f = tempfile.NamedTemporaryFile()
        conf['sa_auth']['log_file'] = f.name
        try:
            app = conf.make_wsgi_app()
        except OSError:
            # Ignore this error, as github actions don't allow to write temporary files.
            pytest.skip("GitHub doesn't allow to write temporary files")

    def test_sqla_auth_middleware_no_backend(self):
        conf = AppConfig(root_controller=RootController())
        conf["sa_auth.enabled"] = False
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadata(),
                                'cookie_secret':'12345'})
        conf.make_wsgi_app()

        with pytest.raises(KeyError):
            authenticators = [x[0] for x in config['sa_auth.authenticators']]
        #assert 'cookie' in authenticators
        #assert len(authenticators) == 1


    def test_sqla_auth_no_authenticate_meth(self):
        conf = AppConfig(root_controller=RootController())
        conf["sa_auth.enabled"] = True
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadata(),
                                'cookie_secret':'12345'})

        with pytest.raises(TGConfigError) as e:
            conf.make_wsgi_app()
        assert "missing authenticate" in str(e.value)

    def test_tgauthmetadata_auth_middleware(self):
        conf = AppConfig(root_controller=RootController())
        conf["sa_auth.enabled"] = True
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'authenticators':UncopiableList([('default', None)])})
        conf.make_wsgi_app()

        authenticators = [x[0] for x in config['sa_auth.authenticators']]
        assert 'cookie' in authenticators
        assert 'tgappauth' in authenticators

    def test_auth_setup_default_identifier(self):
        conf = AppConfig(root_controller=RootController())
        conf["sa_auth.enabled"] = True
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                  'dbsession': None,
                                  'user_class':None,
                                  'cookie_secret':'12345',
                                  'identifiers': UncopiableList([('default', None)])})
        conf.make_wsgi_app()

        identifiers = [x[0] for x in tg.config['sa_auth.identifiers']]
        assert 'cookie' in identifiers

    def test_auth_setup_custom_identifier(self):
        conf = AppConfig(root_controller=RootController())
        conf["sa_auth.enabled"] = True
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                'dbsession': None,
                                'user_class':None,
                                'cookie_secret':'12345',
                                'identifiers': UncopiableList([('custom', None)])})
        conf.make_wsgi_app()

        identifiers = [x[0] for x in config['sa_auth.identifiers']]
        assert 'custom' in identifiers

    def test_auth_middleware_doesnt_touch_authenticators(self):
        # Checks that the auth middleware process doesn't touch original authenticators
        # list, to prevent regressions on this.
        conf = AppConfig(root_controller=RootController())
        conf["sa_auth.enabled"] = True
        conf['sa_auth'].update({'authmetadata': ApplicationAuthMetadataWithAuthentication(),
                                'dbsession': None,
                                'user_class':None,
                                'cookie_secret':'12345',
                                'authenticators':[('default', None)]})
        conf.make_wsgi_app()

        authenticators = [x[0] for x in conf['sa_auth.authenticators']]
        assert len(authenticators) == 1

    def test_tgauthmetadata_loginpwd(self):
        who_authenticator = _AuthMetadataAuthenticator(ApplicationAuthMetadataWithAuthentication(), using_password=True)
        assert who_authenticator.authenticate({}, {}) == None

    def test_tgauthmetadata_nologinpwd(self):
        who_authenticator = _AuthMetadataAuthenticator(ApplicationAuthMetadataWithAuthentication(), using_password=False)
        assert who_authenticator.authenticate({}, {}) == 1

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

        def track_app(app):
            # Save a reference to the plain TGApp before it's wrapped by middlewares.
            track_app.app = app
            return app

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.package = PackageWithModel()
        conf.make_wsgi_app(wrap_app=track_app)

        testmode, __, __ = track_app.app._setup_app_env({'paste.registry':FakeRegistry()})
        assert testmode is False

        testmode, __, __ = track_app.app._setup_app_env({'paste.registry':FakeRegistry(),
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
        conf['errorpage.enabled'] = False
        conf['errorpage.status_codes'] = (403, 404)
        conf['errorpage.handle_exceptions'] = False
        app = conf.make_wsgi_app(full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=403)
        assert 'ERROR!!!' not in resp, resp

    def test_custom_500_json(self):
        class ErrorController(TGController):
            @expose(content_type="text/html")
            @expose('json', content_type="application/json")
            def document(self, *args, **kw):
                return dict(a=5)

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

        resp = app.get('/test', status=500,
                       headers={'Accept': 'application/json'})
        assert '{"a": 5}' in resp.text, resp
        assert 'application/json' == resp.content_type

    def test_errorware_configuration(self):
        class RootController(TGController):
            @expose()
            def test(self, *args, **kwargs):
                return 'HI'

        conf = AppConfig(minimal=True, root_controller=RootController())
        app = conf.make_wsgi_app(full_stack=True,
                                 **{'trace_errors.error_email': 'test@domain.com'})
        app = TestApp(app)
        resp = app.get('/test')
        assert 'HI' in resp, resp

        assert config['tg.errorware']['error_email'] == 'test@domain.com'
        assert config['tg.errorware']['error_subject_prefix'] == 'WebApp Error: '
        assert config['tg.errorware']['error_message'] == 'An internal server error occurred'

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
        assert config['renderers'] == ['json', 'broken']
        assert config['render_functions']['broken'] == 'BROKEN'

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

        conf.make_wsgi_app(full_stack=True)
        assert config['renderers'] == ['json']

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

        conf = AppConfig(root_controller=RootController())
        conf['errorpage.enabled'] = True
        app = conf.make_wsgi_app(debug=True, full_stack=True)
        app = TestApp(app)

        resp = app.get('/test', status=500, expect_errors=True)
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

        class FakeHelpers(object):
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
