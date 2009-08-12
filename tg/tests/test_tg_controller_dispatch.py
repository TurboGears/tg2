# -*- coding: utf-8 -*-

import tg, pylons
from tg.controllers import TGController, CUSTOM_CONTENT_TYPE, \
                           WSGIAppController, RestController
from tg.decorators import expose, validate, override_template, lookup, default
from routes import Mapper
from routes.middleware import RoutesMiddleware
from formencode import validators
from webob import Response, Request
from nose.tools import raises

from tg.tests.base import TestWSGIController, make_app, setup_session_dir, \
                          teardown_session_dir

from wsgiref.simple_server import demo_app
from wsgiref.validate import validator

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

class BeforeController(TGController):
    
    def __before__(self, *args, **kw):
        pylons.c.var = '__my_before__'
    def __after__(self, *args, **kw):
        global_craziness = '__my_after__'
        
    @expose()
    def index(self):
        assert pylons.c.var
        return pylons.c.var

class SubController(object):
    mounted_app = WSGIAppController(wsgi_app)
    
    before = BeforeController()
    

    @expose('genshi')
    def unknown_template(self):
        return "sub unknown template"
    
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


    @expose("genshi:tg.tests.non_overridden")
    def template_override(self, override=False):
        if override:
            override_template(self.template_override, "genshi:tg.tests.overridden")
        return dict()



class SubController3(object):
    @expose()
    def index(self):
        return 'Sub 3'
    
class TGControllerInsideSubRestConroller:
    @expose()
    def index(self):
        return "COMPLICATED"
class SubRestController(RestController):
    
    inside = TGControllerInsideSubRestConroller()
    @expose()
    def new(self):
        return "SUBREST NEW"
    
    @expose()
    def edit(self):
        return "SUBREST EDIT"

    @expose()
    def fxn(self):
        return "SUBREST FXN"

    @expose()
    def get_one(self, id, *args):
        return "SUBREST GETONE"
    
    @expose()
    def put(self, **kw):
        return "SUBREST PUT"

    @expose()
    def post(self, **kw):
        return "SUBREST POST"
    
    @expose()
    def get_all(self):
        return "SUBREST GETALL"
    

    
class RestController3(RestController):
    
    subrest = SubRestController()
    @expose()
    def get_all(self):
        return "SUBREST3 GETALL"

    @expose()
    def get_one(self, id):
        return "REST3 GETONE"
    
    def delete(self):
        """this is intentionally not exposed"""
        
class RestController2(RestController):

    subrest = SubRestController()
    
    @expose()
    def new(self):
        return "REST NEW"
    
    @expose()
    def get_one(self, id, *args):
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
        rest3 = RestController3()
        
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

class LookupHelper:
    
    def __init__(self, var):
        self.var = var
    
    @expose()
    def index(self):
        return self.var
        
class LoookupController(TGController):
    
    @expose()
    def lookup(self, a, *args):
        return LookupHelper(a), args

class DecoDefaultController(TGController):

    @default
    def __0(self, *args):
        return ("recieved the following args (from the url): %s" %list(args))
        
class DecoLookupController(TGController):

    @lookup
    def __0(self, a, *args):
        return LookupHelper(a), args
        
class RemoteErrorHandler(TGController):
    @expose()
    def errors_here(self, *args, **kw):
        return "REMOTE ERROR HANDLER"

class NotFoundController(TGController):pass
    
class BasicTGController(TGController):
    mounted_app = WSGIAppController(wsgi_app)
    
    error_controller = RemoteErrorHandler()
    
    lookup = LoookupController()
    deco_lookup = DecoLookupController()
    deco_default = DecoDefaultController()
    
    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def default(self, *remainder):
        return "Main Default Page called for url /%s"%list(remainder)

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
    def error_handler(self, **kw):
        return 'VALIDATION ERROR HANDLER'
    
    @expose('json')
    @validate(validators={"a":validators.Int()}, error_handler=error_handler)
    def validated_with_error_handler(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode)
        return dict(int=a,str=b)

    @expose('json')
    @validate(validators={"a":validators.Int()}, error_handler=error_controller.errors_here)
    def validated_with_remote_error_handler(self, a, b):
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

class TestRestController(TestWSGIController):
    
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)
    
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

    def test_rest_sub_all(self):
        r = self.app.get('/sub2/rest/rest2/2/subrest')
        assert 'SUBREST GETALL' in r, r

    def test_rest_sub_put(self):
        r = self.app.put('/sub2/rest/rest2/2/subrest')
        assert 'SUBREST PUT' in r, r

    def test_rest_sub_put_with_post_hack(self):
        r = self.app.post('/sub2/rest/rest2/2/subrest?_method=PUT')
        assert 'SUBREST PUT' in r, r

    def test_rest_sub_post(self):
        r = self.app.post('/sub2/rest/rest2/2/subrest')
        assert 'SUBREST POST' in r, r
    
    def test_rest_sub_post(self):
        r = self.app.post('/sub2/rest/rest2/2/subrest')
        assert 'SUBREST POST' in r, r

    def test_rest_sub_new(self):
        r = self.app.get('/sub2/rest/rest2/2/subrest/new')
        assert 'SUBREST NEW' in r, r
    
    def test_rest_sub_edit(self):
        r = self.app.get('/sub2/rest/rest2/2/subrest/edit')
        assert 'SUBREST EDIT' in r, r

    def test_tg_inside_subrest(self):
        r = self.app.get('/sub2/rest/rest2/2/subrest/inside')
        assert 'COMPLICATED' in r, r
        
    def test_fxn_inside_subrest(self):
        r = self.app.get('/sub2/rest/rest2/2/subrest/fxn')
        assert 'SUBREST FXN' in r, r
        
    def test_fxn_inside_subrest_post(self):
        r = self.app.post('/sub2/rest/rest2/subrest/fxn')
        assert 'SUBREST FXN' in r, r
    
    def test_fxn_inside_subrest_post_not_found(self):
        r = self.app.post('/sub2/rest/rest2/2/asdf')
        assert 'Main Default Page called' in r, r
    
    def test_subrest_get_get_one(self):
        r = self.app.get('/sub2/rest/rest2/2/asdf')
        assert 'REST GETONE' in r, r

    def test_subrest_get_not_found(self):
        r = self.app.get('/sub2/rest/rest3/2/asdf')
        assert 'Main Default Page called' in r, r

    def test_fxn_inside_rest3_put_not_found(self):
        r = self.app.put('/sub2/rest/rest3')
        assert 'Main Default Page called' in r, r

    def test_subrest_post_not_found(self):
        r = self.app.delete('/sub2/rest/rest3')
        assert 'Main Default Page called' in r, r

class TestNotFoundController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(NotFoundController)
        
    def test_not_found(self):
        r = self.app.get('/something', status=404)
        assert '404 Not Found' in r, r

    def test_not_found_blank(self):
        r = self.app.get('/', status=404)
        assert '404 Not Found' in r, r

    def test_not_found_unicode(self):
        r = self.app.get('/права', status=404)
        assert '404 Not Found' in r, r

class TestWSGIAppController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        class TestedWSGIAppController(WSGIAppController):
            def __init__(self):
                def test_app(environ, start_response):
                    if environ['CONTENT_LENGTH'] in (-1, '-1'):
                        del environ['CONTENT_LENGTH']
                    return validator(demo_app)(environ, start_response)
                super(TestedWSGIAppController, self).__init__(test_app)
        self.app = make_app(TestedWSGIAppController)

    def test_valid_wsgi(self):
        try:
            r = self.app.get('/some_url')
        except Exception, e:
            raise AssertionError(str(e))
        assert 'some_url' in r

class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)
        
    def test_lookup(self):
        r = self.app.get('/lookup/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_validated_int(self):
        r = self.app.get('/validated_int/1')
        assert '{"response": 1}' in r, r

    def test_new_lookup(self):
        r = self.app.get('/deco_lookup/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_new_default(self):
        r = self.app.get('/deco_default/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_validated_with_error_handler(self):
        r = self.app.get('/validated_with_error_handler?a=asdf')
        msg = 'VALIDATION ERROR HANDLER'
        assert msg in r, r
        
    def test_validated_with_remote_error_handler(self):
        r = self.app.get('/validated_with_remote_error_handler?a=asdf')
        msg = 'REMOTE ERROR HANDLER'
        assert msg in r, r
        
    def test_unknown_template(self):
        r = self.app.get('/sub/unknown_template/')
        msg = 'sub unknown template'
        assert msg in r, r
    
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

    def test_multi_value_kw(self):
        r = self.app.get('/multi_value_kws?foo=1&foo=2')

    def test_before_controller(self):
        r = self.app.get('/sub/before')
        assert '__my_before__' in r, r

    def test_template_override(self):
        r =self.app.get('/sub/template_override')
        assert "Not overridden" in r
        r = self.app.get('/sub/template_override', params=dict(override=True))
        assert "This is overridden." in r
        # now invoke the controller again without override,
        # it should yield the old result
        r =self.app.get('/sub/template_override')
        assert "Not overridden" in r

    def test_unicode_default_dispatch(self):
        r =self.app.get('/sub/äö')
        assert "%C3%A4%C3%B6" in r


