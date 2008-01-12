# -*- coding: utf-8 -*-

import os
from unittest import TestCase
from xmlrpclib import loads, dumps

import webob
import pylons
from paste.registry import Registry
from paste.registry import RegistryManager
from paste.fixture import TestApp
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from paste import httpexceptions

from tg import context
from pylons.util import ContextObj, PylonsContext
from tg.controllers import TurboGearsController
from pylons.testutil import ControllerWrap, SetupCacheGlobal
#import pylons.tests

from beaker.middleware import CacheMiddleware

data_dir = os.path.dirname(os.path.abspath(__file__))

try:
    shutil.rmtree(data_dir)
except:
    pass

default_environ = {
    'pylons.use_webob' : False,
    'pylons.routes_dict': dict(action='index'),
    'paste.config': dict(global_conf=dict(debug=True))
}

def make_app(controller_klass=None, environ=None):
    """Creates a `TestApp` instance.
    """
    if environ is None:
        environ = {}
    environ['pylons.routes_dict'] = {}
    if controller_klass is None:
        controller_klass = TurboGearsController

    app = ControllerWrap(controller_klass)
    app = SetupCacheGlobal(app, environ, setup_cache=True)
    app = CacheMiddleware(app, {}, data_dir=os.path.join(data_dir, 'cache'))
    app = RegistryManager(app)
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
    req = webob.Request.blank(path, environ)
    # setup a Registry
    reg = environ.setdefault('paste.registry', Registry())
    reg.prepare()
    # setup pylons.request to point to our Registry
    reg.register(pylons.request, req)
    # setup tmpl context
    context._push_object(ContextObj())
    return req

class TestWSGIController(TestCase):
    def setUp(self):
        self.environ = default_environ.copy()
        context._push_object(ContextObj())

    def tearDown(self):
        context._pop_object()

    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.post(url, extra_environ=self.environ, params=kargs)
