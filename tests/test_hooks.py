import atexit

import pytest
from webtest import TestApp

import tg
from tests.test_configuration import PackageWithModel
from tg import AppConfig, TGController, expose
from tg.configuration import milestones
from tg.configuration.utils import TGConfigError
from tg.support.hooks import (
    _ApplicationHookRegistration,
    _ControllerHookRegistration,
    _TGGlobalHooksNamespace,
)
from tg.wsgiapp import TGApp


class TestGlobalHooks:
    def setup_method(self):
        milestones._reset_all()

    def teardown_method(self):
        milestones._reset_all()
        tg.hooks._clear()  # Reset hooks

    def test_config_hooks(self):
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
        def configure_new_app_hook(app):
            assert isinstance(app, TGApp)
            visited_hooks.append('configure_new_app')

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.register('before_config', before_config_hook)
        tg.hooks.register('after_config', after_config_hook)
        tg.hooks.register('configure_new_app', configure_new_app_hook)
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert 'before_config' in visited_hooks
        assert 'after_config' in visited_hooks
        assert 'configure_new_app' in visited_hooks

    def test_config_hooks_through_app_config(self):
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
        def configure_new_app_hook(app):
            assert isinstance(app, TGApp)
            visited_hooks.append('configure_new_app')

        conf = AppConfig(minimal=True, root_controller=RootController())
        conf.register_hook('before_config', before_config_hook)
        conf.register_hook('after_config', after_config_hook)
        conf.register_hook('configure_new_app', configure_new_app_hook)
        app = conf.make_wsgi_app()
        app = TestApp(app)

        assert 'HI!' in app.get('/test')
        assert 'before_config' in visited_hooks
        assert 'after_config' in visited_hooks
        assert 'configure_new_app' in visited_hooks

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

    def test_config_hooks_startup_on_controller(self):
        def f():
            pass

        with pytest.raises(TGConfigError):
            tg.hooks.register('startup', None, controller=f)

    def test_config_hooks_shutdown_on_controller(self):
        def f():
            pass

        with pytest.raises(TGConfigError):
            tg.hooks.register('shutdown', None, controller=f)

    def test_controller_wrapper_using_register(self):
        milestones.config_ready.reach()
        with pytest.raises(ValueError):
            tg.hooks.register('controller_wrapper', None)

    def test_global_controller_wrapper_after_milestone_reached(self):
        milestones.environment_loaded.reach()
        conf = AppConfig(minimal=True)
        conf.register_controller_wrapper(None)

    def test_dedicated_controller_wrapper_after_milestone_reached(self):
        conf = AppConfig(minimal=True)

        def f():
            pass

        milestones.environment_loaded.reach()
        with pytest.raises(TypeError):
            conf.register_controller_wrapper(None, controller=f)

    def test_startup_hook(self):
        executed = []
        def func():
            executed.append(True)

        tg.hooks.register('startup', func)
        conf = AppConfig(minimal=True)
        app = conf.make_wsgi_app()
        assert True in executed, executed

    def test_startup_hook_with_exception(self):
        def func():
            raise Exception

        tg.hooks.register('startup', func)
        conf = AppConfig(minimal=True)
        app = conf.make_wsgi_app()

    def test_shutdown_hook_callable(self):
        _registered_exit_funcs = []
        def _fake_atexit_register(what):
            _registered_exit_funcs.append(what)

        #Temporary replace atexit.register
        _real_register = atexit.register
        atexit.register = _fake_atexit_register

        # Temporary replace the hooks namespace so we register hooks only for this test
        original_hooks, tg.hooks = tg.hooks, _TGGlobalHooksNamespace()

        try:
            executed = []
            def func():
                executed.append(True)

            tg.hooks.register('shutdown', func)
            milestones.config_ready.reach()  # This forces hook registration
            assert func in tg.hooks._hooks['shutdown']
            assert len(_registered_exit_funcs), _registered_exit_funcs
            _registered_exit_funcs[0]()
            assert True in executed, executed
        finally:
            tg.hooks = original_hooks
            atexit.register = _real_register

    def test_disconnect_hooks(self):
        hook1_has_been_called = []
        def hook1_listener():
            hook1_has_been_called.append(True)

        class RootController(TGController):
            @expose()
            def test(self):
                tg.hooks.notify('custom_hook')
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.register('custom_hook', hook1_listener)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test')
        app.get('/test')
        tg.hooks.disconnect('custom_hook', hook1_listener)
        app.get('/test')

        assert len(hook1_has_been_called) == 2, hook1_has_been_called

    def test_disconnect_hooks_multiple_listener(self):
        hook1_has_been_called = []
        def hook1_listener():
            hook1_has_been_called.append(True)

        hook2_has_been_called = []
        def hook2_listener():
            hook2_has_been_called.append(True)

        class RootController(TGController):
            @expose()
            def test(self):
                tg.hooks.notify('custom_hook', controller=RootController.test)
                return 'HI!'

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.register('custom_hook', hook1_listener)
        tg.hooks.register('custom_hook', hook2_listener)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test')
        app.get('/test')
        tg.hooks.disconnect('custom_hook', hook2_listener)
        app.get('/test')

        # Disconnecting an unregistered hook should do nothing.
        tg.hooks.disconnect('unregistered', hook1_listener)

        assert len(hook1_has_been_called) == 3, hook1_has_been_called
        assert len(hook2_has_been_called) == 2, hook2_has_been_called

    def test_disconnect_controller_hooks_multiple_listener(self):
        hook1_has_been_called = []
        def hook1_listener():
            hook1_has_been_called.append(True)

        hook2_has_been_called = []
        def hook2_listener():
            hook2_has_been_called.append(True)

        class RootController(TGController):
            @expose()
            def test(self):
                tg.hooks.notify('custom_hook', controller=RootController.test)
                return 'HI!'

            @expose()
            def test2(self):
                tg.hooks.notify('custom_hook', controller=RootController.test2)
                return 'HI'

        conf = AppConfig(minimal=True, root_controller=RootController())
        tg.hooks.register('custom_hook', hook1_listener, controller=RootController.test)
        tg.hooks.register('custom_hook', hook2_listener)
        conf.package = PackageWithModel()
        app = conf.make_wsgi_app()
        app = TestApp(app)

        app.get('/test')
        app.get('/test')
        app.get('/test2')

        assert len(hook1_has_been_called) == 2, hook1_has_been_called
        assert len(hook2_has_been_called) == 3, hook2_has_been_called

        tg.hooks.disconnect('custom_hook', hook1_listener, controller=RootController.test)

        app.get('/test')
        app.get('/test')

        assert len(hook1_has_been_called) == 2, hook1_has_been_called
        assert len(hook2_has_been_called) == 5, hook2_has_been_called

    def test_hooks_describe_themselves(self):
        apphook = _ApplicationHookRegistration(None, "fakename", lambda x:x)
        apphook_repr = repr(apphook)
        assert apphook_repr.startswith("<ApplicationHookRegistration: 'fakename' <function")
        
        controllerhook = _ControllerHookRegistration(None, "fakename", lambda x:x)
        controllerhook_repr = repr(controllerhook)
        assert controllerhook_repr.startswith("<ControllerHookRegistration: 'fakename' <function")
        