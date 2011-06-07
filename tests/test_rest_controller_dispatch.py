# -*- coding: utf-8 -*-

import tg, pylons
from tg.util import no_warn
from tg.controllers import TGController, RestController
from tg.controllers.dispatcher import DispatchState
from tg.decorators import expose, validate, override_template
from routes import Mapper
from routes.middleware import RoutesMiddleware
from formencode import validators
from webob import Response, Request
from nose.tools import raises

from tests.base import TestWSGIController, make_app, setup_session_dir, \
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


class LookupHelper:
    def __init__(self, var):
        self.var = var

    @expose()
    def index(self):
        return self.var


class LookupController(TGController):

    @expose()
    def _lookup(self, a, *args):
        return LookupHelper(a), args

class DeprecatedLookupController(TGController):
    @expose()
    def lookup(self, a, *args):
        return LookupHelper(a), args

class LookupAlwaysHelper:
    """for testing _dispatch"""

    def __init__(self, var):
        self.var = var

    def _setup_wsgiorg_routing_args(self, url_path, remainder, params):
        pass

    @expose()
    def always(self, *args, **kwargs):
        return 'always go here'

    def _dispatch(self, state, remainder):
        state.add_method(self.always, remainder)
        return state

class LookupAlwaysController(TGController):


    @expose()
    def _lookup(self, a, *args):
        return LookupAlwaysHelper(a), args

class CustomDispatchingSubController(TGController):

    @expose()
    def always(self, *args, **kwargs):
        return 'always go here'

    def _dispatch(self, state, remainder):
        state.add_method(self.always, remainder)
        return state

class OptionalArgumentRestController(RestController):
    @expose()
    def get_one(self, optional=None):
        return "SUBREST GET ONE"
    @expose()
    def put(self, optional=None):
        return "SUBREST PUT"
    @expose()
    def post(self, optional=None):
        return "SUBREST POST"
    @expose()
    def edit(self, optional=None):
        return "SUBREST EDIT"
    @expose()
    def new(self, optional=None):
        return "SUBREST NEW"
    @expose()
    def get_delete(self, optional=None):
        return "SUBREST GET DELETE"
    @expose()
    def post_delete(self, optional=None):
        return "SUBREST POST DELETE"

class RequiredArgumentRestController(RestController):
    @expose()
    def get_one(self, something):
        return "SUBREST GET ONE"
    @expose()
    def put(self, something):
        return "SUBREST PUT"
    @expose()
    def post(self, something):
        return "SUBREST POST"
    @expose()
    def edit(self, something):
        return "SUBREST EDIT"
    @expose()
    def new(self):
        return "SUBREST NEW"
    @expose()
    def get_delete(self, something):
        return "SUBREST GET DELETE"
    @expose()
    def post_delete(self, something):
        return "SUBREST POST DELETE"

class VariableSubRestController(RestController):
    @expose()
    def get_one(self, *args):
        return "SUBREST GET ONE"
    @expose()
    def put(self, *args):
        return "SUBREST PUT"
    @expose()
    def edit(self, *args):
        return "SUBREST EDIT"
    @expose()
    def new(self, *args):
        return "SUBREST NEW"
    @expose()
    def get_delete(self, *args):
        return "SUBREST GET DELETE"
    @expose()
    def post_delete(self, *args):
        return "SUBREST POST DELETE"

class SubRestController(RestController):
    @expose()
    def get_all(self):
        return "SUBREST GET ALL"
    @expose()
    def get_one(self, id):
        return "SUBREST GET ONE"
    @expose()
    def new(self):
        return "SUBREST NEW"
    @expose()
    def edit(self, id):
        return "SUBREST EDIT"
    @expose()
    def post(self):
        return "SUBREST POST"
    @expose()
    def put(self, id):
        return "SUBREST PUT"
    @expose()
    def fxn(self):
        return "SUBREST FXN"
    @expose()
    def get_delete(self, id):
        return "SUBREST GET DELETE"
    @expose()
    def post_delete(self, id):
        return "SUBREST POST DELETE"


class VariableRestController(RestController):
    subrest = SubRestController()
    vsubrest = VariableSubRestController()

    @expose()
    def get_all(self):
        return "REST GET ALL"
    @expose()
    def get_one(self, *args):
        return "REST GET ONE"
    @expose()
    def get_delete(self, *args):
        return "REST GET DELETE"
    @expose()
    def post_delete(self, *args):
        return "REST POST DELETE"

class ExtraRestController(RestController):
    @expose()
    def get_all(self):
        return "REST GET ALL"
    @expose()
    def get_one(self, id):
        return "REST GET ONE"
    @expose()
    def get_delete(self, id):
        return "REST GET DELETE"
    @expose()
    def post_delete(self, id):
        return "REST POST DELETE"

    class sub(TGController):
        @expose()
        def index(self):
            return "REST SUB INDEX"

    subrest = SubRestController()
    optsubrest = OptionalArgumentRestController()
    reqsubrest = RequiredArgumentRestController()

    _custom_actions = ['archive']

    @expose()
    def post_archive(self):
        return 'got to post archive'

    @expose()
    def get_archive(self):
        return 'got to get archive'

class BasicRestController(RestController):

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
    def other(self):
        return "REST OTHER"

    _custom_actions = ['archive']

    @expose()
    def archive(self):
        return 'got to archive'

class EmptyRestController(RestController):
    pass

class SubController(TGController):
    rest = BasicRestController()

    @expose()
    def sub_method(self, arg):
        return 'sub %s'%arg

class BasicTGController(TGController):

    sub = SubController()
    custom_dispatch = CustomDispatchingSubController()
    lookup = LookupController()
    deprecated_lookup = LookupController()
    lookup_dispatch = LookupAlwaysController()
    rest  = BasicRestController()
    rest2 = ExtraRestController()
    rest3 = VariableRestController()
    empty = EmptyRestController()

    @expose()
    def index(self, **kwargs):
        return 'hello world'

    @expose()
    def default(self, *remainder):
        return "Main Default Page called for url /%s"%list(remainder)

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

    def test_lookup(self):
        r = self.app.get('/lookup/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_deprecated_lookup(self):
        r = self.app.get('/deprecated_lookup/EYE')
        msg = 'EYE'
        assert msg in r, r

    def test_lookup_with_dispatch(self):
        r = self.app.get('/lookup_dispatch/EYE')
        msg = 'always'
        assert msg in r, r

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

    def test_custom_dispatch(self):
        resp = self.app.get('/custom_dispatch/army of darkness')
        assert "always" in resp, resp

class TestRestController(TestWSGIController):

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_post(self):
        r = self.app.post('/rest/')
        assert 'REST POST' in r, r

    def _test_non_resty(self):
        r = self.app.post('/rest/non_resty_thing')
        assert 'non_resty' in r, r

    def test_custom_action_simple_get(self):
        r = self.app.get('/rest/archive')
        assert 'got to archive' in r, r

    def test_custom_action_simple_post(self):
        r = self.app.post('/rest/archive')
        assert 'got to archive' in r, r

    def test_custom_action_simple_post_args(self):
        r = self.app.post('/rest?_method=archive')
        assert 'got to archive' in r, r

    def test_custom_action_get(self):
        r = self.app.get('/rest2/archive')
        assert 'got to get archive' in r, r

    def test_custom_action_post(self):
        r = self.app.post('/rest2?_method=archive')
        assert 'got to post archive' in r, r

    def test_get(self):
        r = self.app.get('/rest/')
        assert 'REST GET' in r, r

    def test_put(self):
        r = self.app.put('/rest/')
        assert 'REST PUT' in r, r

    def test_put_post(self):
        r = self.app.post('/rest?_method=PUT')
        assert 'REST PUT' in r, r

    def test_put_get(self):
        r = self.app.get('/rest?_method=PUT', status=405)

    def test_put_post(self):
        r = self.app.post('/rest', params={'_method':'PUT'})
        assert 'REST PUT' in r, r

    def test_get_delete_bad(self):
        r = self.app.get('/rest?_method=DELETE', status=405)

    def test_delete(self):
        r = self.app.delete('/rest/')
        assert 'REST DELETE' in r, r

    def test_post_delete(self):
        r = self.app.post('/rest/', params={'_method':'DELETE'})
        assert 'REST DELETE' in r, r

    def test_get_all(self):
        r = self.app.get('/rest2/')
        assert 'REST GET ALL' in r, r

    def test_get_one(self):
        r = self.app.get('/rest2/1')
        assert 'REST GET ONE' in r, r

    def test_get_delete(self):
        r = self.app.get('/rest2/1/delete')
        assert 'REST GET DELETE' in r, r

    def test_post_delete(self):
        r = self.app.post('/rest2/1', params={'_method':'DELETE'})
        assert 'REST POST DELETE' in r, r

    def test_post_delete_var(self):
        r = self.app.post('/rest3/a/b/c', params={'_method':'DELETE'})
        assert 'REST POST DELETE' in r, r

    def test_get_delete_var(self):
        r = self.app.get('/rest3/a/b/c/delete')
        assert 'REST GET DELETE' in r, r

    def test_get_method(self):
        r = self.app.get('/rest/other')
        assert 'REST OTHER' in r, r

    @no_warn
    def test_get_sub_controller(self):
        r = self.app.get('/rest2/sub')
        assert 'REST SUB INDEX' in r, r

    @no_warn
    def test_put_sub_controller(self):
        r = self.app.put('/rest2/sub')
        assert 'REST SUB INDEX' in r, r

    def test_post_sub_controller(self):
        r = self.app.post('/rest2/sub')
        assert 'REST SUB INDEX' in r, r

    def test_post_miss(self):
        r = self.app.post('/rest2/something')
        assert "/['rest2', 'something']" in r, r

    def test_get_empty(self):
        r = self.app.get('/empty/')
        assert "/['empty']" in r, r

    def test_post_empty(self):
        r = self.app.post('/empty/')
        assert "/['empty']" in r, r

    def test_put_empty(self):
        r = self.app.put('/empty/')
        assert "/['empty']" in r, r

    @no_warn
    def test_delete_empty(self):
        r = self.app.delete('/empty/')
        assert "/['empty']" in r, r

    def test_put_miss(self):
        r = self.app.put('/rest/something')
        assert "/['rest', 'something']" in r, r

    def test_delete_miss(self):
        r = self.app.delete('/rest/something')
        assert "/['rest', 'something']" in r, r

    def test_get_miss(self):
        r = self.app.get('/rest2/something/else')
        assert "/['rest2', 'something', 'else']" in r, r

    def test_post_method(self):
        r = self.app.post('/rest/other')
        assert 'REST OTHER' in r, r

    def test_new_method(self):
        r = self.app.post('/rest/new')
        assert 'REST NEW' in r, r

    def test_edit_method(self):
        r = self.app.get('/rest/1/edit')
        assert 'REST EDIT' in r, r

    def test_delete_method(self):
        r = self.app.delete('/rest/other', status=405)

    def test_sub_with_rest_delete(self):
        r = self.app.delete('/sub/rest/')
        assert 'REST DELETE' in r, r 

    def test_put_method(self):
        r = self.app.put('/rest/other')
        assert 'REST OTHER' in r, r

    def test_sub_get_all_method(self):
        r = self.app.get('/rest2/1/subrest')
        assert 'SUBREST GET ALL' in r, r

    def test_var_sub_get_all_method(self):
        r = self.app.get('/rest3/1/3/3/subrest')
        assert 'SUBREST GET ALL' in r, r
        r = self.app.get('/rest3/1/3/subrest')
        assert 'SUBREST GET ALL' in r, r
        r = self.app.get('/rest3/subrest')
        assert 'SUBREST GET ALL' in r, r

    def test_var_sub_get_one_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/1')
        assert 'SUBREST GET ONE' in r, r
        r = self.app.get('/rest3/1/3/subrest/1')
        assert 'SUBREST GET ONE' in r, r
        r = self.app.get('/rest3/subrest/1')
        assert 'SUBREST GET ONE' in r, r

    def test_var_sub_edit_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/1/edit')
        assert 'SUBREST EDIT' in r, r
        r = self.app.get('/rest3/1/3/subrest/1/edit')
        assert 'SUBREST EDIT' in r, r
        r = self.app.get('/rest3/subrest/1/edit')
        assert 'SUBREST EDIT' in r, r

    def test_var_sub_edit_var_method(self):
        r = self.app.get('/rest3/1/3/3/vsubrest/1/edit')
        assert 'SUBREST EDIT' in r, r
        r = self.app.get('/rest3/1/3/vsubrest/1/a/edit')
        assert 'SUBREST EDIT' in r, r
        r = self.app.get('/rest3/vsubrest/edit')
        assert 'SUBREST EDIT' in r, r

    def test_var_sub_delete_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/1/delete')
        assert 'SUBREST GET DELETE' in r, r
        r = self.app.get('/rest3/1/3/subrest/1/delete')
        assert 'SUBREST GET DELETE' in r, r
        r = self.app.get('/rest3/subrest/1/delete')
        assert 'SUBREST GET DELETE' in r, r

    def test_var_sub_edit_var_method(self):
        r = self.app.get('/rest3/1/3/3/vsubrest/1/edit')
        assert 'SUBREST EDIT' in r, r
        r = self.app.get('/rest3/1/3/vsubrest/1/a/edit')
        assert 'SUBREST EDIT' in r, r
        r = self.app.get('/rest3/vsubrest/edit')
        assert 'SUBREST EDIT' in r, r

    def test_var_sub_new_method(self):
        r = self.app.get('/rest3/1/3/3/subrest/new')
        assert 'SUBREST NEW' in r, r
        r = self.app.get('/rest3/1/3/subrest/new')
        assert 'SUBREST NEW' in r, r
        r = self.app.get('/rest3/subrest/new')
        assert 'SUBREST NEW' in r, r

    def test_var_sub_var_get_one_method(self):
        r = self.app.get('/rest3/1/3/3/vsubrest/1')
        assert 'SUBREST GET ONE' in r, r
        r = self.app.get('/rest3/1/3/vsubrest/1/a')
        assert 'SUBREST GET ONE' in r, r
        r = self.app.get('/rest3/vsubrest/')
        assert 'SUBREST GET ONE' in r, r

    def test_var_sub_var_put_method(self):
        r = self.app.put('/rest3/1/3/3/vsubrest/1')
        assert 'SUBREST PUT' in r, r
        r = self.app.put('/rest3/1/3/vsubrest/1/asdf')
        assert 'SUBREST PUT' in r, r
        r = self.app.put('/rest3/vsubrest/')
        assert 'SUBREST PUT' in r, r

    def test_var_sub_post_method(self):
        r = self.app.post('/rest3/1/3/3/subrest/')
        assert 'SUBREST POST' in r, r
        r = self.app.post('/rest3/1/3/subrest/')
        assert 'SUBREST POST' in r, r
        r = self.app.post('/rest3/subrest/')
        assert 'SUBREST POST' in r, r

    def test_var_sub_put_method(self):
        r = self.app.put('/rest3/1/3/3/subrest/1')
        assert 'SUBREST PUT' in r, r
        r = self.app.put('/rest3/1/3/subrest/1')
        assert 'SUBREST PUT' in r, r
        r = self.app.put('/rest3/subrest/1')
        assert 'SUBREST PUT' in r, r

    def test_var_sub_put_hack_method(self):
        r = self.app.post('/rest3/1/3/3/subrest/1?_method=PUT')
        assert 'SUBREST PUT' in r, r
        r = self.app.post('/rest3/1/3/subrest/1?_method=PUT')
        assert 'SUBREST PUT' in r, r
        r = self.app.post('/rest3/subrest/1?_method=PUT')
        assert 'SUBREST PUT' in r, r

    def test_var_sub_var_delete_method(self):
        r = self.app.delete('/rest3/1/3/3/vsubrest/1')
        assert 'SUBREST POST DELETE' in r, r
        r = self.app.delete('/rest3/1/3/vsubrest/1')
        assert 'SUBREST POST DELETE' in r, r
        r = self.app.delete('/rest3/vsubrest/')
        assert 'SUBREST POST DELETE' in r, r

    def test_var_sub_delete_var_hack_method(self):
        r = self.app.post('/rest3/1/3/3/vsubrest/1?_method=DELETE')
        assert 'SUBREST POST DELETE' in r, r
        r = self.app.post('/rest3/1/3/vsubrest/1?_method=DELETE')
        assert 'SUBREST POST DELETE' in r, r
        r = self.app.post('/rest3/vsubrest?_method=DELETE')
        assert 'SUBREST POST DELETE' in r, r

    def test_var_sub_var_put_hack_method(self):
        r = self.app.post('/rest3/1/3/3/vsubrest/1?_method=PUT')
        assert 'SUBREST PUT' in r, r
        r = self.app.post('/rest3/1/3/vsubrest/1/a?_method=PUT')
        assert 'SUBREST PUT' in r, r
        r = self.app.post('/rest3/vsubrest/?_method=PUT')
        assert 'SUBREST PUT' in r, r

    def test_var_sub_delete_hack_method(self):
        r = self.app.post('/rest3/1/3/3/subrest/1?_method=DELETE')
        assert 'SUBREST POST DELETE' in r, r
        r = self.app.post('/rest3/1/3/subrest/1?_method=DELETE')
        assert 'SUBREST POST DELETE' in r, r
        r = self.app.post('/rest3/subrest/1?_method=DELETE')
        assert 'SUBREST POST DELETE' in r, r

    def test_var_sub_delete_method(self):
        r = self.app.delete('/rest3/1/3/3/subrest/1')
        assert 'SUBREST POST DELETE' in r, r
        r = self.app.delete('/rest3/1/3/subrest/1')
        assert 'SUBREST POST DELETE' in r, r

    def test_sub_new(self):
        r = self.app.get('/rest2/1/subrest/new')
        assert 'SUBREST NEW' in r, r

    def test_sub_edit(self):
        r = self.app.get('/rest2/1/subrest/1/edit')
        assert 'SUBREST EDIT' in r, r

    def test_sub_post(self):
        r = self.app.post('/rest2/1/subrest/')
        assert 'SUBREST POST' in r, r

    def test_sub_put(self):
        r = self.app.put('/rest2/1/subrest/2')
        assert 'SUBREST PUT' in r, r

    def test_sub_post(self):
        r = self.app.post('/rest2/1/subrest/')
        assert 'SUBREST POST' in r, r

    def test_sub_post_opt(self):
        r = self.app.post('/rest2/1/optsubrest/1')
        assert 'SUBREST POST' in r, r
    def test_sub_put_opt(self):
        r = self.app.put('/rest2/1/optsubrest/1')
        assert 'SUBREST PUT' in r, r
    def test_sub_put_opt_hack(self):
        r = self.app.post('/rest2/1/optsubrest/1?_method=PUT')
        assert 'SUBREST PUT' in r, r
    def test_sub_delete_opt_hack(self):
        r = self.app.post('/rest2/1/optsubrest/1?_method=DELETE')
        assert 'SUBREST ' in r, r

    def test_put_post_req(self):
        r = self.app.post('/rest2/reqsubrest', params={'something':'required'})
        assert 'SUBREST POST' in r, r

    def test_sub_put_req(self):
        r = self.app.post('/rest2/reqsubrest', params={'_method':'PUT', 'something':'required'})
        assert 'SUBREST PUT' in r, r

    def test_sub_post_req_bad(self):
        r = self.app.post('/rest2/reqsubrest',)
        assert "['rest2', 'reqsubrest']" in r, r

    def test_sub_delete_hack(self):
        r = self.app.post('/rest2/1/subrest/2?_method=DELETE')
        assert 'SUBREST POST DELETE' in r, r

    def test_sub_get_delete(self):
        r = self.app.get('/rest2/1/subrest/2/delete')
        assert 'SUBREST GET DELETE' in r, r

    def test_sub_post_delete(self):
        r = self.app.delete('/rest2/1/subrest/2')
        assert 'SUBREST POST DELETE' in r, r

    def test_sub_get_fxn(self):
        r = self.app.get('/rest2/1/subrest/fxn')
        assert 'SUBREST FXN' in r, r

    def test_sub_post_fxn(self):
        r = self.app.post('/rest2/1/subrest/fxn')
        assert 'SUBREST FXN' in r, r
