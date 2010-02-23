# -*- coding: utf-8 -*-
import paste.httpexceptions as httpexceptions

import tg
from tg.util import no_warn
import pylons
from tg.controllers import TGController
from tg.decorators import expose

from tg.tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir


def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

class GoodJsonObject(object):
    def __json__(self):
        return {'Json':'Rocks'} 

class BadJsonObject(object):
    pass

class BasicTGController(TGController):

    @expose('json')
    def json(self):
        return dict(a='hello world', b=True)

    @expose('json', exclude_names=["b"])
    def excluded_b(self):
        return dict(a="visible", b="invisible")

    @expose('json')
    @expose('genshi:test', content_type='application/xml')
    def xml_or_json(self):
        return dict(name="John Carter", title='officer', status='missing')

    @expose('json')
    def json_with_object(self):
        return dict(obj=GoodJsonObject())

    @expose('json')
    def json_with_bad_object(self):
        return dict(obj=BadJsonObject())

class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_simple_jsonification(self):
        resp = self.app.get('/json')
        assert '{"a": "hello world", "b": true}' in resp.body

    def test_multi_dispatch_json(self):
        resp = self.app.get('/xml_or_json', headers={'accept':'application/json'})
        assert '''"status": "missing"''' in resp
        assert '''"name": "John Carter"''' in resp
        assert '''"title": "officer"''' in resp
    
    #TODO: Setup genshi search path, and test genshi rendering
    
    #TODO: Add tests for 

    def test_json_with_object(self):
        resp = self.app.get('/json_with_object')
        assert '''"Json": "Rocks"''' in resp.body
    
    @no_warn
    def test_json_with_bad_object(self):
        try:
            resp = self.app.get('/json_with_bad_object')
        except TypeError, e:
            pass
        assert "is not JSON serializable" in str(e)
