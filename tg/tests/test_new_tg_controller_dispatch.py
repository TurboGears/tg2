# -*- coding: utf-8 -*-

import tg, pylons
from tg.controllers import TGController
from tg.decorators import expose, validate, override_template
from routes import Mapper
from routes.middleware import RoutesMiddleware
from formencode import validators
from webob import Response, Request
from nose.tools import raises

from tg.tests.base import TestWSGIController, make_app, setup_session_dir, \
                          teardown_session_dir

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

def wsgi_app(environ, start_response):
    req = Request(environ)
    if req.method == 'POST':
        resp = Response(req.POST['data'])
    else:
        resp = Response("Hello from %s/%s"%(req.script_name, req.path_info))
    return resp(environ, start_response)

class SubController:
    def sub_method(self, arg):
        return 'sub %s'%arg

class BasicTGController(TGController):
    
    sub = SubController()
    
    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def default(self, *remainder):
        return "Main Default Page called for url /%s"%list(remainder)

    #sub = SubController()
    @expose()
    def hello(self, name, silly=None):
        return "Hello " + name


class BasicTGControllerNoDefault(TGController):
    @expose()
    def index(self, **kwargs):
        return 'hello world'
    
class TestTGControllerRoot(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGControllerNoDefault)

    def test_root_default_dispatch(self):
        resp = self.app.get('/i/am/not/a/sub/controller', status=404)

class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)
        
    def test_root_method_dispatch(self):
        resp = self.app.get('/hello/Bob')
        assert "Hello Bob" in resp, resp
        
    def test_root_index_dispatch(self):
        resp = self.app.get('/')
        assert "hello world" in resp, resp

    def test_no_sub_index_dispatch(self):
        resp = self.app.get('/sub/')
        assert "['sub']" in resp, resp
        
    def test_root_default_dispatch(self):
        resp = self.app.get('/i/am/not/a/sub/controller')
        assert "['i', 'am', 'not', 'a', 'sub', 'controller']" in resp, resp

    def test_default_dispatch_not_found_in_sub_controller(self):
        resp = self.app.get('/sub/no/default/found')
        assert "['sub', 'no', 'default', 'found']" in resp, resp

    def test_root_method_dispatch_with_trailing_slash(self):
        resp = self.app.get('/hello/Bob/')
        assert "Hello Bob" in resp, resp
    
    def test_sub_method_dispatch(self):
        resp = self.app.get('/sub/sub_method/army of darkness')
        assert "sub army" in resp, resp
        
