# -*- coding: utf-8 -*-
from paste.fixture import TestApp
from paste.registry import RegistryManager
import paste.httpexceptions as httpexceptions

import tg
import pylons
from tg.controllers import TurboGearsController
from pylons.decorators import expose
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
    @expose()
    def index(self):
        return 'hello world'
    
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
        self.environ['pylons.routes_dict'] = {}
        self.baseenviron.update(self.environ)

    def test_tg_style_default(self):
        resp = self.app.get('/sdfaswdfsdfa') #random string should be caught by the default route
        assert 'Default' in resp.body
    
    def test_tg_style_index(self):
        resp = self.app.get('/index/')
        assert 'hello' in resp.body
        
    def test_tg_style_subcontrolelr_index(self):
        resp = self.app.get('/sub/index')
        assert "sub index" in resp.body
    
    def test_tg_style_subcontroller_default(self):
        resp=self.app.get('/sub/bob/tim/joe')
        assert "bob" in resp.body
        assert 'tim' in resp.body
        assert 'joe' in resp.body 
