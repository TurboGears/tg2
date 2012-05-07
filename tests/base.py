# -*- coding: utf-8 -*-

import os, shutil
from unittest import TestCase
from xmlrpclib import loads, dumps
import warnings

import webob
import beaker
from paste.registry import Registry
from paste.registry import RegistryManager
from webtest import TestApp
from paste import httpexceptions

import tg
from tg import tmpl_context, request_local
from tests.test_stack import app_from_config, TestConfig
from routes import URLGenerator, Mapper

from tg.wsgiapp import ContextObj, TGApp, RequestLocals
from tg.controllers import TGController

from test_stack.baseutils import ControllerWrap, FakeRoutes, default_config

from beaker.middleware import CacheMiddleware

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')

def setup_session_dir():
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

def teardown_session_dir():
    shutil.rmtree(session_dir, ignore_errors=True)

default_map = Mapper()

# Setup a default route for the error controller:
default_map.connect('error/:action/:id', controller='error')
# Setup a default route for the root of object dispatch
default_map.connect('*url', controller='root', action='routes_placeholder')

def make_app(controller_klass=None, environ=None):
    """Creates a `TestApp` instance."""
    if controller_klass is None:
        controller_klass = TGController

    app = TGApp(config=default_config)
    app.controller_classes['root'] = ControllerWrap(controller_klass)

    app = FakeRoutes(app)

    app = RegistryManager(app)
    app = beaker.middleware.SessionMiddleware(app, {}, data_dir=session_dir)
    app = CacheMiddleware(app, {}, data_dir=os.path.join(data_dir, 'cache'))
    app = httpexceptions.make_middleware(app)
    return TestApp(app)

def create_request(path, environ=None):
    """Helper used in test cases to quickly setup a request obj.

    ``path``
        The path will become PATH_INFO
    ``environ``
        Additional environment

    Returns an instance of the `webob.Request` object.
    """
    # setup the environ
    if environ is None:
        environ = {}

    # create a "blank" WebOb Request object
    # using TG Request which is a webob Request plus
    # some compatibility methods
    req = request_local.Request.blank(path, environ)

    # setup a Registry
    reg = environ.setdefault('paste.registry', Registry())
    reg.prepare()

    # Setup turbogears context with request, url and tmpl_context
    tgl = RequestLocals()
    tgl.tmpl_context = ContextObj()
    tgl.request = req
    tgl.url = URLGenerator(default_map, environ)

    request_local.context._push_object(tgl)

    return req

class TestWSGIController(TestCase):
    def setUp(self):
        tmpl_options = {}
        tmpl_options['genshi.search_path'] = ['tests']

        self._tgl = RequestLocals()
        self._tgl.tmpl_context = ContextObj()
        request_local.context._push_object(self._tgl)

        warnings.simplefilter("ignore")
        tg.config.push_process_config(default_config)
        warnings.resetwarnings()
        setup_session_dir()

    def tearDown(self):
        request_local.context._pop_object(self._tgl)
        tg.config.pop_process_config()
        teardown_session_dir()

    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['tg.routes_dict'].update(kargs)

        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')

        return self.app.post(url, extra_environ=self.environ, params=kargs)

