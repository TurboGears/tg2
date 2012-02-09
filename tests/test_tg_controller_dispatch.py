# -*- coding: utf-8 -*-

from wsgiref.simple_server import demo_app
from wsgiref.validate import validator

from formencode import validators

from webob import Response, Request

from pylons.controllers.xmlrpc import XMLRPCController

import tg
from tg import config, tmpl_context
from tg.controllers import (
    TGController, CUSTOM_CONTENT_TYPE, WSGIAppController)
from tg.decorators import expose, validate
from tg.util import no_warn

from tests.base import (
    TestWSGIController, make_app, setup_session_dir, teardown_session_dir)


config['renderers'] = ['genshi', 'mako', 'json']


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


class XMLRpcTestController(XMLRPCController):

    def textvalue(self):
        return 'hi from xmlrpc'

    textvalue.signature = [ ['string'] ]


class BeforeController(TGController):

    def _before(self, *args, **kw):
        tmpl_context.var = '__my_before__'

    def _after(self, *args, **kw):
        global_craziness = '__my_after__'

    @expose()
    def index(self):
        assert tmpl_context.var
        return tmpl_context.var


class NewBeforeController(TGController):

    def _before(self, *args, **kw):
        tmpl_context.var = '__my_before__'
        tmpl_context.args = args
        tmpl_context.params = kw

    def _after(self, *args, **kw):
        global_craziness = '__my_after__'

    @expose()
    def index(self):
        assert tmpl_context.var
        return tmpl_context.var

    @expose()
    def with_args(self, *args, **kw):
        assert tmpl_context.args
        assert tmpl_context.params
        return tmpl_context.var + tmpl_context.params['environ']['webob._parsed_query_vars'][0]['x']


class SubController(object):

    mounted_app = WSGIAppController(wsgi_app)

    before = BeforeController()
    newbefore = NewBeforeController()

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
    def _default(self, *args):
        return "received the following args (from the url): %s" % list(args)

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, **kw)

    @expose()
    def redirect_sub(self):
        tg.redirect('index')

    @expose()
    def hello(self, name):
        return "Why hello, %s!" % name


class SubController3(object):
    @expose()
    def get_all(self):
        return 'Sub 3'


class SubController2(object):

    @expose()
    def index(self):
        tg.redirect('list')

    @expose()
    def list(self, **kw):
        return "hello list"


class LookupHelper:

    def __init__(self, var):
        self.var = var

    @expose()
    def index(self):
        return self.var


class LookupHelperWithArgs:

    @expose()
    def get_here(self, *args):
        return "%s"%args

    @expose()
    def post_with_mixed_args(self, arg1, arg2, **kw):
        return "%s%s" % (arg1, arg2)


class LookupControllerWithArgs(TGController):

    @expose()
    def _lookup(self, *args):
        helper = LookupHelperWithArgs()
        return helper, args


class LookupController(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupHelper(a), args


class LookupWithEmbeddedLookupController(TGController):

    @expose()
    def _lookup(self, *args):
        return LookupControllerWithArgs(), args


class LookupHelperWithIndex:

    @expose()
    def index(self):
        return "helper index"

    @expose()
    def method(self):
        return "helper method"


class LookupControllerWithIndexHelper(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupHelperWithIndex(), args

    @expose()
    def index(self):
        return "second controller with index"


class LookupWithEmbeddedLookupWithHelperWithIndex(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupControllerWithIndexHelper(), args

    @expose()
    def index(self):
        return "first controller with index"


class LookupControllerWithSubcontroller(TGController):

    class SubController(object): pass

    @expose()
    def _lookup(self, a, *args):
        return self.SubController(), args


class RemoteErrorHandler(TGController):
    @expose()
    def errors_here(self, *args, **kw):
        return "remote error handler"


class NotFoundController(TGController):
    pass


class DefaultWithArgsController(TGController):

    @expose()
    def _default(self, a, b=None, **kw):
        return "default with args %s %s" % (a, b)


class DeprecatedDefaultWithArgsController(TGController):

    @expose()
    def default(self, a, b=None, **kw):
        return "deprecated default with args %s %s" % (a, b)


class DefaultWithArgsAndValidatorsController(TGController):

    @expose()
    def failure(self, *args, **kw):
        return "failure"

    @expose()
    @validate(dict(a=validators.Int(), b=validators.StringBool()),
        error_handler=failure)
    def _default(self, a, b=None, **kw):
        return "default with args and validators %s %s"%(a, b)


class SubController4:

    default_with_args = DefaultWithArgsController()
    deprecated_default_with_args = DeprecatedDefaultWithArgsController()


class SubController5:

    default_with_args = DefaultWithArgsAndValidatorsController()


class HelperWithSpecificArgs(TGController):

    @expose()
    def index(self, **kw):
        return str(kw)

    @expose()
    def method(self, arg1, arg2, **kw):
        return str((arg1, arg2, kw))


class SelfCallingLookupController(TGController):

    @expose()
    def _lookup(self, a, *args):
        if a in ['a', 'b', 'c']:
            return SelfCallingLookupController(), args
        a = [a]
        a.extend(args)
        return HelperWithSpecificArgs(), a

    @expose()
    def index(self, *args, **kw):
        return str((args, kw))


class BasicTGController(TGController):

    mounted_app = WSGIAppController(wsgi_app)
    xml_rpc = WSGIAppController(XMLRpcTestController())

    error_controller = RemoteErrorHandler()

    lookup = LookupController()
    lookup_with_args = LookupControllerWithArgs()
    lookup_with_sub = LookupControllerWithSubcontroller()
    self_calling = SelfCallingLookupController()

    @expose(content_type='application/rss+xml')
    def ticket2351(self, **kw):
        return 'test'

    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def _default(self, *remainder):
        return "Main default page called for url /%s" % list(remainder)

    @expose()
    def feed(self, feed=None):
        return feed

    sub = SubController()
    sub2 = SubController2()
    sub4 = SubController4()
    sub5 = SubController5()

    embedded_lookup = LookupWithEmbeddedLookupController()
    embedded_lookup_with_index = LookupWithEmbeddedLookupWithHelperWithIndex()

    @expose()
    def test_args(self, name, one=None, two=2, three=3):
        return "name=%s, one=%s, two=%s, three=%s" % (name, one, two, three)

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, kw)

    @expose()
    def hello(self, name, silly=None):
        return "Hello " + name

    @expose()
    def optional_and_req_args(self, name, one=None, two=2, three=3):
        return "name=%s, one=%s, two=%s, three=%s" % (name, one, two, three)

    @expose()
    def ticket2412(self, arg1):
        return arg1

    @expose()
    def redirect_cookie(self, name):
        tg.response.set_cookie('name', name)
        tg.redirect('/hello_cookie')

    @expose()
    def hello_cookie(self):
        return "Hello " + tg.request.cookies['name']

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
    @validate(validators=dict(some_int=validators.Int()))
    def validated_int(self, some_int):
        assert isinstance(some_int, int)
        return dict(response=some_int)

    @expose('json')
    @validate(validators=dict(a=validators.Int()))
    def validated_and_unvalidated(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode)
        return dict(int=a,str=b)

    @expose()
    def error_handler(self, **kw):
        return 'validation error handler'

    @expose('json')
    @validate(validators=dict(a=validators.Int()),
        error_handler=error_handler)
    def validated_with_error_handler(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode)
        return dict(int=a,str=b)

    @expose('json')
    @validate(validators=dict(a=validators.Int()),
        error_handler=error_controller.errors_here)
    def validated_with_remote_error_handler(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode)
        return dict(int=a,str=b)

    @expose()
    @expose('json')
    def stacked_expose(self):
        return dict(got_json=True)

    @expose('json')
    def bad_json(self):
        return [(1, 'a'), 'b']

    @expose()
    def custom_content_type_in_controller(self):
        tg.response.headers['content-type'] = 'image/png'
        return 'PNG'

    @expose('json', content_type='application/json')
    def custom_content_type_in_controller_charset(self):
        tg.response.headers['content-type'] = 'application/json; charset=utf-8'
        return dict(result='TXT')

    @expose(content_type=CUSTOM_CONTENT_TYPE)
    def custom_content_type_with_ugliness(self):
        tg.response.headers['content-type'] = 'image/png'
        return 'PNG'

    @expose(content_type='image/png')
    def custom_content_type_in_decorator(self):
        return 'PNG'

    @expose()
    def test_204(self, *args, **kw):
        from webob.exc import HTTPNoContent
        raise HTTPNoContent().exception

    @expose()
    def custom_content_type_replace_header(self):
        replace_header(tg.response.headerlist, 'Content-Type', 'text/xml')
        return "<?xml version='1.0'?>"

    @expose()
    def multi_value_kws(sekf, *args, **kw):
        assert kw['foo'] == ['1', '2'], kw


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
                    if environ.get('CONTENT_LENGTH', None) in (-1, '-1'):
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

    def setUp(self, *args, **kargs):
        TestWSGIController.setUp(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_lookup(self):
        r = self.app.get('/lookup/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_lookup_with_sub(self):
        r = self.app.get('/lookup_with_sub/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_lookup_with_args(self):
        r = self.app.get('/lookup_with_args/get_here/got_here')
        msg = 'got_here'
        assert r.body==msg, r

    def test_post_with_mixed_args(self):
        r = self.app.post('/lookup_with_args/post_with_mixed_args/test', params={'arg2': 'time'})
        msg = 'testtime'
        assert r.body==msg, r

    def test_validated_int(self):
        r = self.app.get('/validated_int/1')
        assert '{"response": 1}' in r, r

    def test_validated_with_error_handler(self):
        r = self.app.get('/validated_with_error_handler?a=asdf&b=123')
        msg = 'validation error handler'
        assert msg in r, r

    def test_validated_with_remote_error_handler(self):
        r = self.app.get('/validated_with_remote_error_handler?a=asdf&b=123')
        msg = 'remote error handler'
        assert msg in r, r

    def test_unknown_template(self):
        r = self.app.get('/sub/unknown_template/')
        msg = 'sub unknown template'
        assert msg in r, r

    def test_mounted_wsgi_app_at_root(self):
        r = self.app.get('/mounted_app/')
        assert 'Hello from /mounted_app' in r, r

    def test_mounted_wsgi_app_at_subcontroller(self):
        r = self.app.get('/sub/mounted_app/')
        assert 'Hello from /sub/mounted_app/' in r, r

    def test_request_for_wsgi_app_with_extension(self):
        r = self.app.get('/sub/mounted_app/some_document.pdf')
        assert 'Hello from /sub/mounted_app//some_document.pdf' in r, r

    def test_posting_to_mounted_app(self):
        r = self.app.post('/mounted_app/', params={'data':'Foooo'})
        assert 'Foooo' in r, r

    def test_custom_content_type_replace_header(self):
        s = '''<?xml version="1.0"?>
<methodCall>
<methodName>textvalue</methodName>
</methodCall>
'''
        r = self.app.post('/xml_rpc/', s, [('Content-Type', 'text/xml')])
        assert len(r.headers.getall('Content-Type')) == 1

    def test_response_type(self):
        r = self.app.post('/stacked_expose.json')
        assert 'got_json' in r.body, r

    def test_multi_value_kw(self):
        r = self.app.get('/multi_value_kws?foo=1&foo=2')

    def test_before_controller(self):
        r = self.app.get('/sub/before')
        assert '__my_before__' in r, r

    def test_new_before_controller(self):
        r = self.app.get('/sub/newbefore')
        assert '__my_before__' in r, r

    def test_before_with_args(self):
        r = self.app.get('/sub/newbefore/with_args/1/2?x=5')
        assert '__my_before__5' in r, r

    @no_warn
    def test_unicode_default_dispatch(self):
        r =self.app.get('/sub/äö')
        assert "\\xc3\\xa4\\xc3\\xb6" in r, r

    def test_default_with_empty_second_arg(self):
        r =self.app.get('/sub4/default_with_args/a')
        assert "default with args a None" in r.body, r
        assert "deprecated" not in r.body
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args/a')
        warnings.resetwarnings()
        assert "deprecated default with args a None" in r.body, r

    def test_default_with_args_a_b(self):
        r =self.app.get('/sub4/default_with_args/a/b')
        assert "default with args a b" in r.body, r
        assert "deprecated" not in r.body
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args/a/b')
        warnings.resetwarnings()
        assert "deprecated default with args a b" in r.body, r

    def test_default_with_query_arg(self):
        r =self.app.get('/sub4/default_with_args?a=a')
        assert "default with args a None" in r.body, r
        assert "deprecated" not in r.body
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args?a=a')
        warnings.resetwarnings()
        assert "deprecated default with args a None" in r.body, r

    def test_default_with_validator_fail(self):
        r =self.app.get('/sub5/default_with_args?a=True')
        assert "failure" in r.body, r

    def test_default_with_validator_pass(self):
        r =self.app.get('/sub5/default_with_args?a=66')
        assert "default with args and validators 66 None" in r.body, r

    def test_default_with_validator_pass2(self):
        r =self.app.get('/sub5/default_with_args/66')
        assert "default with args and validators 66 None" in r.body, r

    def test_default_with_validator_fail2(self):
        r =self.app.get('/sub5/default_with_args/True/more')
        assert "failure" in r.body, r

    def test_custom_content_type_in_controller(self):
        resp = self.app.get('/custom_content_type_in_controller')
        assert 'PNG' in resp, resp
        assert resp.headers['Content-Type'] == 'image/png', resp

    def test_custom_content_type_in_controller_charset(self):
        resp = self.app.get('/custom_content_type_in_controller_charset')
        assert 'TXT' in resp, resp
        assert resp.headers['Content-Type'] == 'application/json; charset=utf-8', resp

    def test_custom_content_type_in_decorator(self):
        resp = self.app.get('/custom_content_type_in_decorator')
        assert 'PNG' in resp, resp
        assert resp.headers['Content-Type'] == 'image/png', resp

    def test_custom_content_type_with_ugliness(self):
        #in 2.2 this test can be removed for CUSTOM_CONTENT_TYPE will be removed
        resp = self.app.get('/custom_content_type_with_ugliness')
        assert 'PNG' in resp, resp
        assert resp.headers['Content-Type'] == 'image/png', resp

    def test_removed_spurious_content_type(self):
        r = self.app.get('/test_204')
        assert r.headers.get('Content-Type', 'MISSING') == 'MISSING'

    def test_optional_and_req_args(self):
        resp = self.app.get('/optional_and_req_args/test/one')
        assert "name=test, one=one, two=2, three=3" in  resp, resp

    def test_optional_and_req_args_at_root(self):
        resp = self.app.get('/test_args/test/one')
        assert "name=test, one=one, two=2, three=3" in  resp, resp

    def test_no_args(self):
        resp = self.app.get('/test_args/test/')
        assert "name=test, one=None, two=2, three=3" in  resp, resp

    def test_one_extra_arg(self):
        resp = self.app.get('/test_args/test/1')
        assert "name=test, one=1, two=2, three=3" in  resp, resp

    def test_two_extra_args(self):
        resp = self.app.get('/test_args/test/1/2')
        assert "name=test, one=1, two=2, three=3" in  resp, resp

    def test_three_extra_args(self):
        resp = self.app.get('/test_args/test/1/2/3')
        assert "name=test, one=1, two=2, three=3" in  resp, resp

    def test_extra_args_forces_default_lookup(self):
        resp = self.app.get('/test_args/test/1/2/3/4')
        assert resp.body == """Main default page called for url /['test_args', 'test', '1', '2', '3', '4']""", resp

    def test_not_enough_args(self):
        resp = self.app.get('/test_args/test/1')
        assert "name=test, one=1, two=2, three=3" in  resp, resp

    def test_ticket_2412_with_ordered_arg(self):
        # this is failing
        resp = self.app.get('/ticket2412/Abip%C3%B3n')
        assert """Abipón""" in  resp, resp

    def test_ticket_2412_with_named_arg(self):
        resp = self.app.get('/ticket2412?arg1=Abip%C3%B3n')
        assert """Abipón""" in  resp, resp

    def test_ticket_2351_bad_content_type(self):
        resp = self.app.get('/ticket2351', headers={'Accept':'text/html'})
        assert 'test' in resp, resp

    def test_embedded_lookup_with_index_first(self):
        resp = self.app.get('/embedded_lookup_with_index/')
        assert 'first controller with index' in resp, resp

    def test_embedded_lookup_with_index_second(self):
        resp = self.app.get('/embedded_lookup_with_index/a')
        assert 'second controller with index' in resp, resp

    def test_embedded_lookup_with_index_helper(self):
        resp = self.app.get('/embedded_lookup_with_index/a/b')
        assert 'helper index' in resp, resp

    def test_embedded_lookup_with_index_method(self):
        resp = self.app.get('/embedded_lookup_with_index/a/b/method')
        assert 'helper method' in resp, resp

    def test_self_calling_lookup_simple_index(self):
        resp = self.app.get('/self_calling')
        assert '((), {})' in resp, resp

    def test_self_calling_lookup_method(self):
        resp = self.app.get('/self_calling/a/method/a/b')
        assert "('a', 'b', {})" in resp, resp

    def test_self_calling_lookup_multiple_calls_method(self):
        resp = self.app.get('/self_calling/a/b/c/method/a/b')
        assert "('a', 'b', {})" in resp, resp
