# -*- coding: utf-8 -*-
import os
import tg
from tg.test_stack import TestConfig, app_from_config
from tg.configuration import config
from webtest import TestApp
from nose.tools import eq_
from routes import Mapper

def setup_noDB():
    class TestRoutesConfig(TestConfig):
        def setup_routes(self):
            config['routes.map'] = setup_map(self.paths['controllers'])

    base_config = TestRoutesConfig(folder='dispatch', values={
        'use_sqlalchemy': False,
        'ignore_parameters': ["ignore", "ignore_me"]})
    return app_from_config(base_config)

def setup_map(controller_path):
    # These tests pass with the directory specified and without, but this
    # is the configuration recommended by the 2.0 docs so we'll go with that.
    map = Mapper(directory=controller_path, always_scan=True)

    map.connect('/custom/static',
        controller='routingtest',
        action='static')

    map.connect('/special/{name}/{page}',
        controller='routingtest',
        action='dynamic',
        requirements={'page': '\d+'},
        page=1)

    map.connect('/{controller}/{action}',
        action='index')

    return map

app = setup_noDB()

def test_static_route():
    resp = app.get('/custom/static')
    assert resp.body == 'Routingtest.static'

def test_sane_default_route():
    resp = app.get('/routingtest/static')
    assert resp.body == 'Routingtest.static'

def test_dynamic_route():
    name, page = 'dynamic-name', 2
    resp = app.get('/special/%s/%d' % (name, page))
    assert resp.body.startswith('Routingtest.dynamic')
    assert 'name=[%s]' % name in resp.body
    assert 'page=[%s]' % page in resp.body

def test_dynamic_route_using_default_values():
    name, page = 'another-dynamic-name', 1
    resp = app.get('/special/another-dynamic-name') # note page is omitted here
    assert resp.body.startswith('Routingtest.dynamic')
    assert 'name=[%s]' % name in resp.body
    assert 'page=[%s]' % page in resp.body

def test_kwargs():
    # test for http://trac.turbogears.org/ticket/2303#comment:12
    resp = app.get('/routingtest/kwargs?firstkeyword=1&secondkeyword=blah')
    assert "'firstkeyword': u'1'" in resp.body
    assert "'secondkeyword': u'blah'" in resp.body

