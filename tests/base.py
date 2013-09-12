# -*- coding: utf-8 -*-

import os, shutil
from unittest import TestCase

try:
    from xmlrpclib import loads, dumps
except ImportError:
    from xmlrpc.client import loads, dumps
import warnings

import beaker

from tg.support.registry import Registry, RegistryManager

from webtest import TestApp

import tg
from tg import tmpl_context, request_local
from tg.configuration import milestones

from tg.wsgiapp import ContextObj, TGApp, RequestLocals
from tg.controllers import TGController

from .test_stack.baseutils import ControllerWrap, FakeRoutes, default_config

from beaker.middleware import CacheMiddleware

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')

def setup_session_dir():
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

def teardown_session_dir():
    shutil.rmtree(session_dir, ignore_errors=True)

def make_app(controller_klass=None, environ=None):
    """Creates a `TestApp` instance."""
    if controller_klass is None:
        controller_klass = TGController

    tg.config['renderers'] = default_config['renderers']

    app = TGApp(config=default_config)
    app.controller_classes['root'] = ControllerWrap(controller_klass)

    app = FakeRoutes(app)

    app = RegistryManager(app)
    app = beaker.middleware.SessionMiddleware(app, {}, data_dir=session_dir)
    app = CacheMiddleware(app, {}, data_dir=os.path.join(data_dir, 'cache'))
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

    request_local.context._push_object(tgl)

    return req

class TestWSGIController(TestCase):
    def setUp(self):
        tmpl_options = {}
        tmpl_options['genshi.search_path'] = ['tests']

        self._tgl = RequestLocals()
        self._tgl.tmpl_context = ContextObj()
        request_local.context._push_object(self._tgl)

        # Mark configuration milestones as passed as
        # test sets up a fake configuration
        milestones._reach_all()

        warnings.simplefilter("ignore")
        tg.config.push_process_config(default_config)
        warnings.resetwarnings()
        setup_session_dir()

    def tearDown(self):
        request_local.context._pop_object(self._tgl)
        tg.config.pop_process_config()
        teardown_session_dir()

        # Reset milestones
        milestones._reset_all()

    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['tg.routes_dict'].update(kargs)

        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')

        return self.app.post(url, extra_environ=self.environ, params=kargs)

