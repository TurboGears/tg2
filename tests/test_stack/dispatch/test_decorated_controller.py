# -*- coding: utf-8 -*-
from nose.tools import raises
import os, tg
from tests.test_stack import TestConfig, app_from_config
from webtest import TestApp
from tg.jsonify import JsonEncodeError
from tg.util import no_warn

from nose.tools import eq_
from nose import SkipTest
from tg._compat import PY3, u_

class TestHooks(object):
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
        app = app_from_config(base_config)

        ans = app.get('/echo')
        assert 'WORKED' in ans


class TestExpose(object):
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
        assert exposition.engine == tg.config['default_renderer']
        assert exposition.template == 'nonexisting'


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
        if PY3: raise SkipTest()

        resp = self.app.get('/test_vardec', params={'test-1':'1', 'test-2':2, 'test-':4})
        assert resp.json['test-1'] == '1'
        assert resp.json['test-'] == '4'

    def test_variable_decode(self):
        if PY3: raise SkipTest()

        from formencode.variabledecode import variable_encode
        obj = dict(
            a=['1','2','3'],
            b=dict(c=[dict(d='1')]))
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
