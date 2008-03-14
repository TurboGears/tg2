# -*- coding: utf-8 -*-

import tg, pylons
from tg.controllers import TGController
from pylons.decorators import expose
from routes import Mapper
from routes.middleware import RoutesMiddleware

from tg.tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

class SubController(object):
    @expose()
    def foo(self,):
        return 'sub_foo'

    @expose()
    def index(self):
        return 'sub index'

    @expose()
    def default(self, *args):
        return ("recieved the following args (from the url): %s" %list(args))

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, **kw)

    @expose()
    def redirect_sub(self):
        tg.redirect('index')

    @expose()
    def hello(self, name):
        return "Why HELLO! " + name

class SubController2(object):
    @expose()
    def index(self):
        tg.redirect('list')
    
    @expose()
    def list(self, **kw):
        return "hello list"

class BasicTGController(TGController):
    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def default(self, remainder):
        return "Main Default Page called for url /%s"%remainder

    @expose()
    def feed(self, feed=None):
        return feed
        
    sub = SubController()
    sub2 = SubController2()

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, kw)

    @expose()
    def hello(self, name, silly=None):
        return "Hello " + name

    @expose()
    def redirect_cookie(self, name):
        pylons.response.set_cookie('name', name)
        tg.redirect('/hello_cookie')

    @expose()
    def hello_cookie(self):
        return "Hello " + pylons.request.cookies['name']

    @expose()
    def flash_redirect(self):
        tg.flash("Wow, flash!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_unicode(self):
        tg.flash(u"Привет, мир!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_after_redirect(self):
        return tg.get_flash()
    
    @expose()
    def flash_status(self):
        return tg.get_status()

    @expose()
    def flash_no_redirect(self):
        tg.flash("Wow, flash!")
        return tg.get_flash() 

class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)
        
    def test_tg_style_default(self):
        resp = self.app.get('/sdfaswdfsdfa') #random string should be caught by the default route
        assert 'Default' in resp.body
    
    def test_url_encoded_param_passing(self):
        resp = self.app.get('/feed?feed=http%3A%2F%2Fdeanlandolt.com%2Ffeed%2Fatom%2F')
        assert "http://deanlandolt.com/feed/atom/" in resp.body
    
    def test_tg_style_index(self):
        resp = self.app.get('/index/')
        assert 'hello' in resp.body
    
    def test_tg_style_subcontroller_index(self):
        resp = self.app.get('/sub/index')
        assert "sub index" in resp.body
    
    def test_tg_style_subcontroller_default(self):
        resp=self.app.get('/sub/bob/tim/joe')
        assert "bob" in resp.body
        assert 'tim' in resp.body
        assert 'joe' in resp.body
    
    def test_redirect_absolute(self):
        resp = self.app.get('/redirect_me?target=/')
        assert resp.status == 302, resp.status
        assert resp.header('location') == 'http://localhost/', resp.headers
        resp = resp.follow()
        self.failUnless('hello world' in resp)
    
    def test_redirect_relative(self):
        resp = self.app.get('/redirect_me?target=hello&name=abc').follow()
        self.failUnless('Hello abc' in resp)
        resp = self.app.get('/sub/redirect_me?target=hello&name=def').follow()
        self.failUnless('Why HELLO! def' in resp)
        resp = self.app.get('/sub/redirect_me?target=../hello&name=ghi').follow()
        self.failUnless('Hello ghi' in resp)
    
    def test_redirect_external(self):
        resp = self.app.get('/redirect_me?target=http://example.com')
        assert resp.status == 302 and dict(resp.headers)['location'] == 'http://example.com'
    
    def test_redirect_param(self):
        resp = self.app.get('/redirect_me?target=/hello&name=paj').follow()
        self.failUnless('Hello paj' in resp)
        resp = self.app.get('/redirect_me?target=/hello%3fname=pbj').follow()
        self.failUnless('Hello pbj' in resp)
        resp = self.app.get('/redirect_me?target=/hello%3fsilly=billy&name=pcj').follow()
        self.failUnless('Hello pcj' in resp)
    
    def test_redirect_cookie(self):
        resp = self.app.get('/redirect_cookie?name=stefanha').follow()
        self.failUnless('Hello stefanha' in resp)
    
    def test_subcontroller_redirect_subindex(self):
        resp=self.app.get('/sub/redirect_sub').follow()
        self.failUnless('sub index' in resp)
    
    def test_subcontroller_redirect_sub2index(self):
        resp=self.app.get('/sub2/').follow()
        self.failUnless('hello list' in resp)
    
    def test_subcontroller_redirect_no_slash_sub2index(self):
        resp=self.app.get('/sub2/').follow()
        self.failUnless('hello list' in resp)
    
    def test_flash_redirect(self):
        resp = self.app.get('/flash_redirect').follow()
        self.failUnless('Wow, flash!' in resp, resp)
    
    def test_flash_no_redirect(self):
        resp = self.app.get('/flash_no_redirect')
        self.failUnless('Wow, flash!' in resp, resp)
    
    def test_flash_unicode(self):
        resp = self.app.get('/flash_unicode').follow()
        content = resp.body.decode('utf8')
        self.failUnless(u'Привет, мир!' in content, resp)
    
    def test_flash_status(self):
        resp = self.app.get('/flash_status')
        self.failUnless('status_ok'in resp, resp)    