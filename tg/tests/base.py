# -*- coding: utf-8 -*-

import os, shutil
from unittest import TestCase
from xmlrpclib import loads, dumps

import webob
import beaker
import pylons
from paste.registry import Registry
from paste.registry import RegistryManager
from webtest import TestApp
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from paste import httpexceptions

import tg
from tg import tmpl_context
from pylons import url
from routes import URLGenerator, Mapper
from tg.util import Bunch
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

default_map = Mapper()

# Setup a default route for the error controller:
default_map.connect('error/:action/:id', controller='error')
# Setup a default route for the root of object dispatch
default_map.connect('*url', controller='root', action='routes_placeholder')

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
    url._push_object(URLGenerator(default_map, environ))
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
        setup_session_dir()

    def tearDown(self):
        tmpl_context._pop_object(self._ctx)
        pylons.buffet._pop_object(self._buffet)
        teardown_session_dir()
        
    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)

        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')

        return self.app.post(url, extra_environ=self.environ, params=kargs)

