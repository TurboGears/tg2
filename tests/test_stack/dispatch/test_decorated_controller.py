# -*- coding: utf-8 -*-
import tg
from tests.test_stack import TestConfig, app_from_config
from tg.configuration import milestones
from tg.decorators import Decoration


class TestHooks(object):
    def setup_method(self):
        milestones._reset_all()
        tg.hooks._clear()

    def teardown_method(self):
        milestones._reset_all()
        tg.hooks._clear()

    def test_hooks_syswide(self):
        base_config = TestConfig(folder = 'dispatch',
                                 values = {'use_sqlalchemy': False,
                                           'use_toscawidgets': False,
                                           'use_toscawidgets2': False,
                                           'ignore_parameters': ["ignore", "ignore_me"]
                                 })

        def hook(*args, **kw):
            tg.tmpl_context.echo = 'WORKED'

        tg.hooks.register('before_call', hook)
        app = app_from_config(base_config, reset_milestones=False)

        ans = app.get('/echo')
        assert 'WORKED' in ans


class TestExpose(object):
    def setup_method(self):
        milestones.renderers_ready._reset()

    def teardown_method(self):
        milestones.renderers_ready._reset()

    def test_unregisterd_renderers_detection(self):
        #If no renderers are available we should just issue a warning
        #and avoid crashing. Simply bypass rendering availability check.
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        old_renderers = tg.config['renderers']
        tg.config['renderers'] = []

        @tg.expose('mako:nonexisting')
        def func(*args, **kw):
            pass

        tg.config['renderers'] = old_renderers

    def test_use_default_renderer(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        exposition = tg.expose('nonexisting')
        exposition._resolve_options()

        assert exposition.engine == tg.config['default_renderer']
        assert exposition.template == 'nonexisting'

    def test_expose_without_function_does_nothing(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        exposition = tg.expose('nonexisting')
        exposition._apply()

        assert exposition._func is None
        assert exposition.engine is None

    def test_expose_idempotent(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        app = app_from_config(base_config)

        exposition = tg.expose('nonexisting')

        @exposition
        @exposition
        def func(*args, **kw):
            pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(func)
        assert len(deco.engines) == 1, deco.engines

class TestDecorators(object):
    def setup_method(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        self.app = app_from_config(base_config)

    def test_without_trailing_slash(self):
        resp = self.app.get('/without_tslash/', status=301)
        assert resp.headers['Location'].endswith('/without_tslash')

    def test_with_trailing_slash(self):
        resp = self.app.get('/with_tslash', status=301)
        assert resp.headers['Location'].endswith('/with_tslash/')

    def test_with_engine(self):
        resp = self.app.get('/onmaster')
        assert 'mainslave' in resp

    def test_with_engine_without_params(self):
        resp = self.app.get('/onmaster_without_params?first=1&second=1')
        assert 'mainslave' in resp

    def test_with_engine_nopop(self):
        resp = self.app.get('/onmaster?second=1')
        assert 'master' in resp
        assert 'second' in resp

    def test_with_engine_pop(self):
        resp = self.app.get('/onmaster?first=1')
        assert 'master' in resp
        assert 'first' not in resp

    def test_with_engine_using_list(self):
        resp = self.app.get('/onmaster_withlist?first=1')
        assert 'master' in resp
        assert 'first' not in resp
