# -*- coding: utf-8 -*-
from wsgiref.simple_server import demo_app
from wsgiref.validate import validator
from nose.tools import raises

from tests.test_validation import validators

from webob import Response, Request
from tg._compat import unicode_text, u_

try:
    from pylons.controllers.xmlrpc import XMLRPCController
except ImportError:
    try:
        from xmlrpclib import dumps
    except ImportError:
        from xmlrpc.client import dumps

    class XMLRPCController(object):
        def __call__(self, environ, start_response):
            raw_response = self.textvalue()
            response = dumps((raw_response,), methodresponse=True, allow_none=False).encode('utf-8')

            headers = []
            headers.append(('Content-Length', str(len(response))))
            headers.append(('Content-Type', 'text/xml'))
            start_response("200 OK", headers)
            return [response]


import tg
from tg import config, tmpl_context
from tg.controllers import (TGController, WSGIAppController)
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
        tmpl_context.params = dict(environ=tg.request.environ, **kw)

    def _after(self, *args, **kw):
        global_craziness = '__my_after__'

    def _visit(self, *remainder, **params):
        tmpl_context.visit = 'visited'

    @expose()
    def index(self):
        assert tmpl_context.var
        return tmpl_context.var

    @expose()
    def with_args(self, *args, **kw):
        assert tmpl_context.args
        assert tmpl_context.params
        return tmpl_context.var + tmpl_context.params['environ']['webob._parsed_query_vars'][0]['x']

    @expose()
    def visited(self):
        return tmpl_context.visit

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
        return "received the following args (from the url): %s" % ', '.join(args)

    @expose()
    def redirect_me(self, target, **kw):
        tg.redirect(target, **kw)

    @expose()
    def redirect_sub(self):
        tg.redirect('index')

    @expose()
    def hello(self, name):
        return "Why hello, %s!" % name

    @expose()
    def get_controller_state(self):
        return '/'.join([p[0] for p in tg.request.controller_state.controller_path])

class SubController3(object):
    @expose()
    def get_all(self):
        return 'Sub 3'

    @expose()
    def controller_url(self, using_tmpl_context='false', *args):
        if using_tmpl_context == 'true':
            return tmpl_context.controller_url
        else:
            return tg.request.controller_url

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

class NotFoundWithIndexController(TGController):
    @expose()
    def index(self, *args, **kw):
        return 'INDEX'

class DefaultWithArgsController(TGController):

    @expose()
    def _default(self, a, b=None, **kw):
        return "default with args %s %s" % (a, b)


class DeprecatedDefaultWithArgsController(TGController):

    @expose()
    def _default(self, a, b=None, **kw):
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
        return str((str(arg1), str(arg2), kw))


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

    @expose()
    def use_wsgi_app(self):
        return tg.use_wsgi_app(wsgi_app)

    @expose(content_type='application/rss+xml')
    def ticket2351(self, **kw):
        return 'test'

    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose(content_type='application/rss+xml')
    def index_unicode(self):
        tg.response.charset = None
        return u_('Hello World')

    @expose()
    def _default(self, *remainder):
        return "Main default page called for url /%s" % [str(r) for r in remainder]

    @expose()
    def feed(self, feed=None):
        return feed

    sub = SubController()
    sub2 = SubController2()
    sub3 = SubController3()
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
        tg.flash(u_("Привет, мир!"))
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
        assert isinstance(b, unicode_text)
        return dict(int=a,str=b)

    @expose()
    def error_handler(self, **kw):
        return 'validation error handler'

    @expose('json')
    @validate(validators=dict(a=validators.Int()),
        error_handler=error_handler)
    def validated_with_error_handler(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
        return dict(int=a,str=b)

    @expose('json')
    @validate(validators=dict(a=validators.Int()),
        error_handler=error_controller.errors_here)
    def validated_with_remote_error_handler(self, a, b):
        assert isinstance(a, int)
        assert isinstance(b, unicode_text)
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
        return b'PNG'

    @expose('json', content_type='application/json')
    def custom_content_type_in_controller_charset(self):
        tg.response.headers['content-type'] = 'application/json; charset=utf-8'
        return dict(result='TXT')

    @expose(content_type='image/png')
    def custom_content_type_in_decorator(self):
        return b'PNG'

    @expose()
    def test_204(self, *args, **kw):
        from webob.exc import HTTPNoContent
        raise HTTPNoContent()

    @expose()
    def custom_content_type_replace_header(self):
        replace_header(tg.response.headerlist, 'Content-Type', 'text/xml')
        return "<?xml version='1.0'?>"

    @expose()
    def multi_value_kws(sekf, *args, **kw):
        assert kw['foo'] == ['1', '2'], kw

    @expose()
    def with_routing_args(self, **kw):
        return str(tg.request._controller_state.routing_args)

    @expose('json')
    @expose('genshi')
    @expose()
    def get_response_type(self):
        return dict(ctype=tg.request.response_type)

    @expose()
    def hello_ext(self, *args):
        return str(tg.request.response_ext)

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
        r = self.app.get('/%D0%BF%D1%80%D0%B0%D0%B2%D0%B0', status=404)
        assert '404 Not Found' in r, r

class TestNotFoundWithIndexController(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(NotFoundWithIndexController)

    def test_not_found(self):
        r = self.app.get('/something', status=404)
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
        self.app = make_app(TestedWSGIAppController, config_options={
            'make_body_seekable': True
        })

    def test_valid_wsgi(self):
        try:
            r = self.app.get('/some_url')
        except Exception as e:
            raise AssertionError(str(e))
        assert 'some_url' in r

class TestWSGIAppControllerNotHTML(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        class TestedWSGIAppController(WSGIAppController):
            def __init__(self):
                def test_app(environ, start_response):
                    start_response('200 OK', [('Content-type','text/plain'),
                                              ('Content-Length', '5')])
                    return [b'HELLO']
                super(TestedWSGIAppController, self).__init__(test_app)
        self.app = make_app(TestedWSGIAppController, config_options={
            'make_body_seekable': True
        })

    def test_right_wsgi_headers(self):
        r = self.app.get('/some_url')
        assert 'HELLO' in r
        assert r.content_length == 5
        assert r.content_type == 'text/plain'

class TestTGController(TestWSGIController):
    def setUp(self, *args, **kargs):
        TestWSGIController.setUp(self, *args, **kargs)
        self.app = make_app(BasicTGController, config_options={
            'make_body_seekable': True
        })

    def test_enable_routing_args(self):
        self.app = make_app(BasicTGController, config_options={
            'enable_routing_args': True
        })

        r = self.app.get('/with_routing_args?a=1&b=2&c=3')
        assert 'a' in str(r)
        assert 'b' in str(r)
        assert 'c' in str(r)

    def test_response_without_charset(self):
        r = self.app.get('/index_unicode')
        assert 'Hello World' in r, r
        assert 'charset=utf-8' in str(r), r

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
        assert r.body.decode('utf-8')==msg, r

    def test_post_with_mixed_args(self):
        r = self.app.post('/lookup_with_args/post_with_mixed_args/test', params={'arg2': 'time'})
        msg = 'testtime'
        assert r.body.decode('utf-8')==msg, r

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

    def test_use_wsgi_app(self):
        r = self.app.get('/use_wsgi_app')
        assert '/use_wsgi_app' in r, r

    def test_custom_content_type_replace_header(self):
        s = '''<?xml version="1.0"?>
<methodCall>
<methodName>textvalue</methodName>
</methodCall>
'''
        r = self.app.post('/xml_rpc/', s, [('Content-Type', 'text/xml')])
        assert len(r.headers.getall('Content-Type')) == 1, r.headers.getall('Content-Type')
        assert r.headers['Content-Type'] == 'text/xml'

    def test_response_type(self):
        r = self.app.post('/stacked_expose.json')
        assert 'got_json' in r.body.decode('utf-8'), r

    def test_multi_value_kw(self):
        r = self.app.get('/multi_value_kws?foo=1&foo=2')

    def test_before_controller(self):
        r = self.app.get('/sub/before')
        assert '__my_before__' in r, r

    def test_new_before_controller(self):
        r = self.app.get('/sub/newbefore')
        assert '__my_before__' in r, r

    def test_visit_entry_point(self):
        r = self.app.get('/sub/newbefore/visited')
        assert 'visited' in r, r

    def test_before_with_args(self):
        r = self.app.get('/sub/newbefore/with_args/1/2?x=5')
        assert '__my_before__5' in r, r

    def test_before_controller_mounted_in_subpath(self):
        r = self.app.get('/subpath/sub/before', extra_environ={'SCRIPT_NAME':'/subpath'})
        assert '__my_before__' in r, r

    def test_empty_path_after_script_name_removal(self):
        r = self.app.get('/')
        check_again_response = r.text

        r = self.app.get('/subpath', extra_environ={'SCRIPT_NAME':'/subpath'})
        assert r.text == check_again_response, r

    def test_before_controller_without_script_name(self):
        req = self.app.RequestClass.blank('/sub/before', {})
        req.environ.pop('SCRIPT_NAME')
        r = self.app.do_request(req, status=None, expect_errors=False)
        assert '__my_before__' in r, r

    @no_warn
    def test_unicode_default_dispatch(self):
        r =self.app.get('/sub/%C3%A4%C3%B6')
        assert u_("äö") in r.body.decode('utf-8'), r

    def test_default_with_empty_second_arg(self):
        r =self.app.get('/sub4/default_with_args/a')
        assert "default with args a None" in r.body.decode('utf-8'), r
        assert "deprecated" not in r.body.decode('utf-8')
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args/a')
        warnings.resetwarnings()
        assert "deprecated default with args a None" in r.body.decode('utf-8'), r

    def test_default_with_args_a_b(self):
        r =self.app.get('/sub4/default_with_args/a/b')
        assert "default with args a b" in r.body.decode('utf-8'), r
        assert "deprecated" not in r.body.decode('utf-8')
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args/a/b')
        warnings.resetwarnings()
        assert "deprecated default with args a b" in r.body.decode('utf-8'), r

    def test_default_with_query_arg(self):
        r =self.app.get('/sub4/default_with_args?a=a')
        assert "default with args a None" in  r.body.decode('utf-8'), r
        assert "deprecated" not in  r.body.decode('utf-8')
        import warnings
        warnings.filterwarnings('ignore', category=DeprecationWarning)
        r = self.app.get('/sub4/deprecated_default_with_args?a=a')
        warnings.resetwarnings()
        assert "deprecated default with args a None" in  r.body.decode('utf-8'), r

    def test_default_with_validator_fail(self):
        r =self.app.get('/sub5/default_with_args?a=True')
        assert "failure" in  r.body.decode('utf-8'), r

    def test_default_with_validator_pass(self):
        r =self.app.get('/sub5/default_with_args?a=66')
        assert "default with args and validators 66 None" in  r.body.decode('utf-8'), r

    def test_default_with_validator_pass2(self):
        r =self.app.get('/sub5/default_with_args/66')
        assert "default with args and validators 66 None" in  r.body.decode('utf-8'), r

    def test_default_with_validator_fail2(self):
        r =self.app.get('/sub5/default_with_args/True/more')
        assert "failure" in  r.body.decode('utf-8'), r

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

    def test_removed_spurious_content_type(self):
        r = self.app.get('/test_204')
        assert r.headers.get('Content-Type', 'MISSING') == 'MISSING'

    def test_optional_and_req_args(self):
        resp = self.app.get('/optional_and_req_args/test/one')
        assert "name=test, one=one, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_optional_and_req_args_at_root(self):
        resp = self.app.get('/test_args/test/one')
        assert "name=test, one=one, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_no_args(self):
        resp = self.app.get('/test_args/test/')
        assert "name=test, one=None, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_one_extra_arg(self):
        resp = self.app.get('/test_args/test/1')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_two_extra_args(self):
        resp = self.app.get('/test_args/test/1/2')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_three_extra_args(self):
        resp = self.app.get('/test_args/test/1/2/3')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_extra_args_forces_default_lookup(self):
        resp = self.app.get('/test_args/test/1/2/3/4')
        assert resp.body.decode('utf-8') == """Main default page called for url /['test_args', 'test', '1', '2', '3', '4']""", resp

    def test_not_enough_args(self):
        resp = self.app.get('/test_args/test/1')
        assert "name=test, one=1, two=2, three=3" in  resp.body.decode('utf-8'), resp

    def test_ticket_2412_with_ordered_arg(self):
        resp = self.app.get('/ticket2412/Abip%C3%B3n')
        assert u_("""Abipón""") in resp.body.decode('utf-8'), resp

    def test_ticket_2412_with_named_arg(self):
        resp = self.app.get('/ticket2412?arg1=Abip%C3%B3n')
        assert u_("""Abipón""") in resp.body.decode('utf-8'), resp

    def test_ticket_2351_bad_content_type(self):
        resp = self.app.get('/ticket2351', headers={'Accept':'text/html'})
        assert 'test' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_first(self):
        resp = self.app.get('/embedded_lookup_with_index/')
        assert 'first controller with index' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_second(self):
        resp = self.app.get('/embedded_lookup_with_index/a')
        assert 'second controller with index' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_helper(self):
        resp = self.app.get('/embedded_lookup_with_index/a/b')
        assert 'helper index' in resp.body.decode('utf-8'), resp

    def test_embedded_lookup_with_index_method(self):
        resp = self.app.get('/embedded_lookup_with_index/a/b/method')
        assert 'helper method' in resp.body.decode('utf-8'), resp

    def test_self_calling_lookup_simple_index(self):
        resp = self.app.get('/self_calling')
        assert '((), {})' in resp.body.decode('utf-8'), resp

    def test_self_calling_lookup_method(self):
        resp = self.app.get('/self_calling/a/method/a/b')
        assert "('a', 'b', {})" in resp.body.decode('utf-8'), resp

    def test_self_calling_lookup_multiple_calls_method(self):
        resp = self.app.get('/self_calling/a/b/c/method/a/b')
        assert "('a', 'b', {})" in resp.body.decode('utf-8'), resp

    def test_controller_state(self):
        resp = self.app.get('/sub/get_controller_state')
        assert '/sub' in resp

    def test_response_type_json(self):
        resp = self.app.get('/get_response_type.json')
        assert 'json' in resp

    def test_response_type_html(self):
        resp = self.app.get('/get_response_type.html')
        assert 'html' in resp

    def test_extensions_single(self):
        resp = self.app.get('/hello_ext.html')
        assert resp.body.decode('ascii') == '.html', resp.body

    def test_extensions_missing(self):
        resp = self.app.get('/hello_ext')
        assert resp.body.decode('ascii') == 'None', resp.body

    def test_extensions_two(self):
        resp = self.app.get('/hello_ext.json.html')
        assert 'Main default page' in resp, resp
        assert 'hello_ext.json' in resp, resp

    def test_extensions_three(self):
        resp = self.app.get('/hello_ext.jpg.json.html')
        assert 'Main default page' in resp, resp
        assert 'hello_ext.jpg.json' in resp, resp

    def test_controller_url(self):
        resp = self.app.get('/sub3/controller_url/false/a/b/c')
        assert resp.text == 'sub3/controller_url', resp.text

    def test_controller_url_backward_compatibility(self):
        resp = self.app.get('/sub3/controller_url/true/a/b/c')
        assert resp.text == 'sub3/controller_url', resp.text


class TestNestedWSGIAppWithoutSeekable(TestWSGIController):
    def setUp(self, *args, **kargs):
        TestWSGIController.setUp(self, *args, **kargs)
        self.app = make_app(BasicTGController, config_options={
            'make_body_seekable': False
        })

    @raises(RuntimeError)
    def test_missing_body_seekable_trapped(self):
        self.app.get('/mounted_app')
