# -*- coding: utf-8 -*-
from paste.fixture import TestApp
from paste.registry import RegistryManager
import paste.httpexceptions as httpexceptions

import tg
import pylons
from pylons.controllers import WSGIController
from tg.controllers import TurboGearsController
from tg.decorators import expose
from pylons.controllers.util import redirect_to
from routes import Mapper
from routes.middleware import RoutesMiddleware

from __init__ import TestWSGIController, SetupCacheGlobal, ControllerWrap

class SubController(object):
    @expose()
    def foo(self):
        return 'sub_foo'
    
    @expose()
    def index(self):
        return 'sub index'
    
    @expose()
    def default(self, *args):
        return ("recieved the following args (from the url): %s" %list(args))

class BasicTGController(TurboGearsController):
    def __before__(self):
        pylons.response.headers['Cache-Control'] = 'private'
    
    def __after__(self):
        pylons.response.set_cookie('big_message', 'goodbye')
    
    @expose()
    def index(self):
        return 'hello world'

    def yield_fun(self):
        def its():
            x = 0
            while x < 100:
                yield 'hi'
                x += 1
        return its()
    
    def strme(self):
        return "hi there"
    
    def use_redirect(self):
        pylons.response.set_cookie('message', 'Hello World')
        exc = httpexceptions.get_exception(301)
        raise exc('/elsewhere')
    
    def header_check(self):
        pylons.response.headers['Content-Type'] = 'text/plain'
        return "Hello all!"
    
    def nothing(self):
        return
    
    @expose()    
    def default(self, remainder):
        return "Main Default Page called for url /%s"%remainder    
        
    sub = SubController()


class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        app = ControllerWrap(BasicTGController)
        app = self.sap = SetupCacheGlobal(app, self.baseenviron)
        app = RegistryManager(app)
        self.app = TestApp(app)
        
    def setUp(self):
        TestWSGIController.setUp(self)
        self.baseenviron.update(self.environ)

    def test_wsgi_call(self):
        resp = self.get_response()
        assert 'hello world' in resp
    
    def test_yield_wrapper(self):
        resp = self.get_response(action='yield_fun')
        assert 'hi' * 100 in resp

    def test_404(self):
        self.environ['paste.config']['global_conf']['debug'] = False
        self.environ['pylons.routes_dict']['action'] = 'notthere'
        resp = self.app.get('/', status=404)
        assert resp.status == 404
    
    def test_private_func(self):
        self.baseenviron['pylons.routes_dict']['action'] = '_private'
        resp = self.app.get('/', status=404)
        assert resp.status == 404
    
    def test_strme_func(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'strme'
        resp = self.app.get('/')
        assert "hi there" in resp
    
    def test_header_check(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'header_check'
        resp = self.app.get('/')
        assert "Hello all!" in resp
        assert resp.response.headers['Content-Type'] == 'text/plain'
        assert resp.response.headers['Cache-Control'] == 'private'
        assert resp.header('Content-Type') == 'text/plain'
    
    def test_redirect(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'use_redirect'
        resp = self.app.get('/', status=301)

    def test_nothing(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'nothing'
        resp = self.app.get('/')
        assert '' == resp.body
        assert resp.response.headers['Cache-Control'] == 'private'

    def test_unicode_action(self):
        self.baseenviron['pylons.routes_dict']['action'] = u'ОбсуждениеКомпаний'
        resp = self.app.get('/', status=404)

    def test_tg_style_default(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'route' 
        self.baseenviron['pylons.routes_dict']['url']= 'sdfaswdfsdfa' #Do TG dispatch
        resp = self.app.get('/sdfaswdfsdfa') #random string should be caught by the default route
        assert 'Default' in resp.body
    
    def test_tg_style_index(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'route' #Do TG dispatch
        self.baseenviron['pylons.routes_dict']['url']= 'index'
        resp = self.app.get('/index/')
        assert 'hello' in resp.body
        
    def test_tg_style_subcontrolelr_index(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'route' #Do TG dispatch
        self.baseenviron['pylons.routes_dict']['url']= 'sub/index'
        resp = self.app.get('/sub/index')
        assert "sub index" in resp.body
    
    def test_tg_style_subcontroller_default(self):
        self.baseenviron['pylons.routes_dict']['action'] = 'route' #Do TG dispatch
        self.baseenviron['pylons.routes_dict']['url']= 'sub/bob/tim/joe'
        resp=self.app.get('/sub/bob/tim/joe')
        assert "bob" in resp.body
        assert 'tim' in resp.body
        assert 'joe' in resp.body 
