# -*- coding: utf-8 -*-

import tg, pylons
from tg.controllers import TGController, CUSTOM_CONTENT_TYPE, WSGIAppController, RestController
from tg.decorators import expose, validate
from routes import Mapper
from routes.middleware import RoutesMiddleware
from formencode import validators
from webob import Response, Request
from nose.tools import raises

from tg.tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir

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

class SubController(object):
    mounted_app = WSGIAppController(wsgi_app)
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

class SubController3(object):
    @expose()
    def index(self):
        return 'Sub 3'
    
class RestController2(RestController):

    @expose()
    def new(self):
        return "REST NEW"
    
    @expose()
    def get_one(self, *args):
        return "REST GETONE"
    @expose()
    def get_all(self):
        return "REST GETALL"
    
    def post(self):
        """this is intentionally not exposed"""
        
    @expose()
    def get_delete(self, *args, **kw):
        return "REST GETDEL"
    @expose()
    def post_delete(self, *args):
        return "REST POSTDEL"

class SubController2(object):
    @expose()
    def index(self):
        tg.redirect('list')

    @expose()
    def list(self, **kw):
        return "hello list"

    class rest(RestController):

        sub3 = SubController3()
        rest2 = RestController2()
        
        @expose()
        def get(self):
            return "REST GET"
        @expose()
        def post(self):
            return "REST POST"
        @expose()
        def put(self):
            return "REST PUT"
        @expose()
        def delete(self):
            return "REST DELETE"
        @expose()
        def new(self):
            return "REST NEW"
        
        @expose()
        def edit(self, *args, **kw):
            return "REST EDIT"
        
        @expose()
        def non_resty_thing(self):
            return "non_resty"

class BasicTGController(TGController):
    mounted_app = WSGIAppController(wsgi_app)
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

    @expose('json')
    @validate(validators={"some_int": validators.Int()})
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json')
    @validate(validators={"a":validators.Int()})
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode)
        return dict(int=a,str=b)

    @expose()
    @expose('json')
    def stacked_expose(self, tg_format=None):
        return dict(got_json=True)

    @expose(content_type=CUSTOM_CONTENT_TYPE)
    def custom_content_type(self):
        pylons.response.headers['content-type'] = 'image/png'
        return 'PNG'

    @expose()
    def multi_value_kws(sekf, *args, **kw):
        assert kw['foo'] == ['1', '2'], kw

class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_mounted_wsgi_app_at_root(self):
        r = self.app.get('/mounted_app/')
        self.failUnless('Hello from /mounted_app' in r, r)

    def test_mounted_wsgi_app_at_subcontroller(self):
        r = self.app.get('/sub/mounted_app/')
        self.failUnless('Hello from /sub/mounted_app/' in r, r)

    def test_request_for_wsgi_app_with_extension(self):
        r = self.app.get('/sub/mounted_app/some_document.pdf')
        self.failUnless('Hello from /sub/mounted_app//some_document.pdf' in r, r)

    def test_posting_to_mounted_app(self):
        r = self.app.post('/mounted_app/', params={'data':'Foooo'})
        self.failUnless('Foooo' in r, r)

    def test_response_type(self):
        r = self.app.post('/stacked_expose.json')
        assert 'got_json' in r, r

    def test_deprecated_tg_format_no_mimetype(self):
        r = self.app.post('/stacked_expose?tg_format=json')
        assert 'got_json' in r, r

    @raises(Exception)
    def test_unknown_mimetype(self):
        r = self.app.post('stacket_expose?tg_format=crazy_unknown_thing')

    def test_rest_post(self):
        r = self.app.post('/sub2/rest/')
        assert 'REST POST' in r, r

    def test_rest_non_resty(self):
        r = self.app.post('/sub2/rest/non_resty_thing')
        assert 'non_resty' in r, r
        
    def test_rest_sub_controller(self):
        r = self.app.get('/sub2/rest/sub3')
        assert 'Sub 3' in r, r

    def test_rest_get(self):
        r = self.app.get('/sub2/rest/')
        assert 'REST GET' in r, r

    def test_rest_delete(self):
        r = self.app.delete('/sub2/rest/')
        assert 'REST DELETE' in r, r

    def test_rest_put(self):
        r = self.app.put('/sub2/rest/')
        assert 'REST PUT' in r, r

    def test_rest_get_all(self):
        r = self.app.get('/sub2/rest/rest2/')
        assert 'REST GETALL' in r, r

    def test_rest_get_one(self):
        r = self.app.get('/sub2/rest/rest2/1')
        assert 'REST GETONE' in r, r

    def test_rest_get_delete_ugly(self):
        r = self.app.get('/sub2/rest/rest2/1?_method=delete')
        assert 'REST GETDEL' in r, r
    
    def test_rest_get_delete(self):
        r = self.app.get('/sub2/rest/rest2/1/delete')
        assert 'REST GETDEL' in r, r
    
    def test_rest_post_delete(self):
        r = self.app.post('/sub2/rest/rest2/1/delete')
        assert 'REST POSTDEL' in r, r
        
    def test_rest_nested_new(self):
        r = self.app.get('/sub2/rest/rest2/new')
        assert 'REST NEW' in r, r
        
    def test_multi_value_kw(self):
        r = self.app.get('/multi_value_kws?foo=1&foo=2')
