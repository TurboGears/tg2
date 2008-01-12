# -*- coding: utf-8 -*-

import os
from unittest import TestCase
from xmlrpclib import loads, dumps

from paste.registry import RegistryManager
from paste.fixture import TestApp
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from paste import httpexceptions

from tg import context
from pylons.util import ContextObj, PylonsContext
from tg.controllers import TurboGearsController
from pylons.testutil import ControllerWrap, SetupCacheGlobal
#import pylons.tests

data_dir = os.path.dirname(os.path.abspath(__file__))

try:
    shutil.rmtree(data_dir)
except:
    pass

def make_app(controller_klass=None, environ=None):
    """Creates a `TestApp` instance.
    """
    if environ is None:
        environ = {}
    environ['pylons.routes_dict'] = {}
    if controller_klass is None:
        controller_klass = TurboGearsController

    app = ControllerWrap(controller_klass)
    app = SetupCacheGlobal(app, environ)
    app = RegistryManager(app)
    app = httpexceptions.make_middleware(app)
    return TestApp(app)

class TestWSGIController(TestCase):
    def setUp(self):
        self.environ = {'pylons.routes_dict':dict(action='index'),
                        'paste.config':dict(global_conf=dict(debug=True))}
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
