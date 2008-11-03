# -*- coding: utf-8 -*-

import os, shutil
from unittest import TestCase
from xmlrpclib import loads, dumps

import webob
import beaker
import pylons
from paste.registry import Registry
from paste.registry import RegistryManager
from paste.fixture import TestApp
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from paste import httpexceptions

import tg
from tg import tmpl_context
from tg.util import Bunch
from tg.configuration import AppConfig
from pylons.util import ContextObj, PylonsContext
from pylons.controllers.util import Request, Response
from tg.controllers import TGController
from pylons.testutil import ControllerWrap, SetupCacheGlobal

from beaker.middleware import CacheMiddleware


data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')

def setup_session_dir():
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)
    
def teardown_session_dir():
    shutil.rmtree(session_dir, ignore_errors=True)


default_environ = {
    'pylons.use_webob' : True,
    'pylons.routes_dict': dict(action='index'),
    'paste.config': dict(global_conf=dict(debug=True))
}

def make_app(controller_klass=None, environ=None):
    """Creates a `TestApp` instance."""
    if environ is None:
        environ = {}
    environ['pylons.routes_dict'] = {}
    environ['pylons.routes_dict']['action'] = "routes_placeholder"

    if controller_klass is None:
        controller_klass = TGController

    app = ControllerWrap(controller_klass)
    app = SetupCacheGlobal(app, environ, setup_cache=True, setup_session=True)    
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
    environ.update(default_environ)
    # create a "blank" WebOb Request object
    # using Pylon's Request which is a webob Request plus
    # some compatibility methods
    req = Request.blank(path, environ)
    # setup a Registry
    reg = environ.setdefault('paste.registry', Registry())
    reg.prepare()
    # setup pylons.request to point to our Registry
    reg.register(pylons.request, req)
    # setup tmpl context
    tmpl_context._push_object(ContextObj())
    return req

class TestWSGIController(TestCase):
    def setUp(self):
        tmpl_options = {}
        tmpl_options['genshi.search_path'] = ['tests']
        self._ctx = ContextObj()
        tmpl_context._push_object(self._ctx)
        self._buffet = pylons.templating.Buffet(
            default_engine='genshi',tmpl_options=tmpl_options
            )
        pylons.buffet._push_object(self._buffet)


    def tearDown(self):
        tmpl_context._pop_object(self._ctx)
        pylons.buffet._pop_object(self._buffet)
        
    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.post(url, extra_environ=self.environ, params=kargs)

class TestConfig(AppConfig):

    def __init__(self, folder, values=None):
        AppConfig.__init__(self)
        #First we setup some base values that we know will work
        self.renderers = ['genshi'] 
        self.render_functions = tg.util.Bunch()
        self.package = tg.tests.test_stack
        self.default_renderer = 'genshi'
        self.globals = self
        self.helpers = {}
        self.auth_backend = None
        self.auto_reload_templates = False
        self.use_legacy_renderer = True
        self.serve_static = False
        

        #Then we overide those values with what was passed in
        for key, value in values.items():
            setattr(self, key, value)

        
        root = "."
        test_base_path = os.path.join(root,'tg', 'tests', 'test_stack',)
        test_config_path = os.path.join(test_base_path, folder)
        print test_config_path
        self.paths=tg.util.Bunch(
                    root=test_base_path,
                    controllers=os.path.join(test_config_path, 'controllers'),
                    static_files=os.path.join(test_config_path, 'public'),
                    templates=[os.path.join(test_config_path, 'templates')]
                    )

    def setup_helpers_and_globals(self):
        tg.config['pylons.app_globals'] = self.globals
        tg.config['pylons.h'] = self.helpers
