# -*- coding: utf-8 -*-

import tg
from tg.controllers import TurboGearsController
from pylons.decorators import expose
from routes import Mapper
from routes.middleware import RoutesMiddleware

from tg.tests import TestWSGIController, make_app

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

    @expose()
    def redirect_me(self):
        tg.redirect('/')

    @expose()
    def flash_redirect(self):
        tg.flash("Wow, flash!")
        tg.redirect("/flash_after_redirect")

    @expose()
    def flash_after_redirect(self):
        return tg.get_flash()

    @expose()
    def flash_no_redirect(self):
        tg.flash("Wow, flash!")
        return tg.get_flash()

class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        self.app = make_app(BasicTGController, self.baseenviron)

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

    def test_redirect(self):
        resp = self.app.get('/redirect_me').follow()
        self.failUnless('hello world' in resp)

    def test_flash_redirect(self):
        resp = self.app.get('/flash_redirect').follow()
        self.failUnless('Wow, flash!' in resp, resp)

    def test_flash_no_redirect(self):
        resp = self.app.get('/flash_no_redirect')
        self.failUnless('Wow, flash!' in resp, resp)
