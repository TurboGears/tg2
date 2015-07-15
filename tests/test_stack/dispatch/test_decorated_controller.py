# -*- coding: utf-8 -*-
from nose.tools import raises
import os, tg
from tests.test_stack import TestConfig, app_from_config
from tg.configuration.hooks import _TGGlobalHooksNamespace
from tg.decorators import Decoration
from tg.configuration import milestones
from tg.util import Bunch


class TestHooks(object):
    def setUp(self):
        milestones._reset_all()
        tg.hooks = _TGGlobalHooksNamespace()

    def tearDown(self):
        milestones._reset_all()
        tg.hooks = _TGGlobalHooksNamespace()

    def test_hooks_syswide(self):
        base_config = TestConfig(folder = 'dispatch',
                                 values = {'use_sqlalchemy': False,
                                           'use_toscawidgets': False,
                                           'use_toscawidgets2': False,
                                           'ignore_parameters': ["ignore", "ignore_me"]
                                 })

        def hook(*args, **kw):
            tg.tmpl_context.echo = 'WORKED'

        base_config.register_hook('before_call', hook)
        app = app_from_config(base_config, reset_milestones=False)

        ans = app.get('/echo')
        assert 'WORKED' in ans

    def test_decoration_run_hooks_backward_compatibility(self):
        # TODO: Remove test when Decoration.run_hooks gets removed

        def func(*args, **kw):
            pass

        def hook(*args, **kw):
            hook.did_run = True
        hook.did_run = False

        milestones.renderers_ready.reach()
        tg.hooks.register('before_call', hook, controller=func)

        deco = Decoration.get_decoration(func)
        deco.run_hooks(Bunch(config=None), 'before_call')

        assert hook.did_run is True

class TestExpose(object):
    def setUp(self):
        milestones.renderers_ready._reset()

    def tearDown(self):
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
    def setup(self):
        base_config = TestConfig(folder = 'dispatch',
            values = {'use_sqlalchemy': False,
                      'use_toscawidgets': False,
                      'use_toscawidgets2': False,
                      'ignore_parameters': ["ignore", "ignore_me"]
            })

        self.app = app_from_config(base_config)

    def test_variabledecode_fail(self):
        resp = self.app.get('/test_vardec', params={'test-1': '1',
                                                    'test-2': 2,
                                                    'test--repetitions': 'hi'})
        assert resp.json['test-1'] == '1', resp.json
        assert resp.json['test--repetitions'] == 'hi', resp.json
        assert 'test' not in resp.json, resp.json

    def test_variabledecode_partial_fail(self):
        resp = self.app.get('/test_vardec', params={'test-1': '1',
                                                    'test-2': 2,
                                                    'test-': 4})
        assert resp.json['test-1'] == '1'
        assert resp.json['test-'] == '4'
        assert len(resp.json['test']) == 2

    def test_variable_decode(self):
        from formencode.variabledecode import variable_encode
        obj = dict(a=['1','2','3'], b=dict(c=[dict(d='1')]))
        params = variable_encode(dict(obj=obj), add_repetitions=False)
        resp = self.app.get('/test_vardec', params=params)
        assert resp.json['obj'] == obj, (resp.json['obj'], obj)

    def test_without_trailing_slash(self):
        resp = self.app.get('/without_tslash/', status=301)
        assert resp.headers['Location'].endswith('/without_tslash')

    def test_with_trailing_slash(self):
        resp = self.app.get('/with_tslash', status=301)
        assert resp.headers['Location'].endswith('/with_tslash/')

    def test_with_engine(self):
        resp = self.app.get('/onmaster')
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
