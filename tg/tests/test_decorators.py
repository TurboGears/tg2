# -*- coding: utf-8 -*-
import paste.httpexceptions as httpexceptions

import tg
import pylons
from tg.controllers import TGController
from pylons.decorators import expose

from turbojson.jsonify import jsonify

from tg.tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

pylons.buffet = pylons.templating.Buffet(default_engine='genshi')

class MyClass(object):
    pass

@jsonify.when('isinstance(obj, MyClass)')
def jsonify_myclass(obj):
    return {'result':'wo-hoo!'}

class BasicTGController(TGController):

    @expose('json')
    def json(self):
        return dict(a='hello world', b=True)

    @expose('json', exclude_names=["b"])
    def excluded_b(self):
        return dict(a="visible", b="invisible")

    @expose('json')
    def custom(self):
        return dict(custom=MyClass())

    @expose('json')
    @expose('genshi:', content_type='application/xml')
    def xml_or_json(self):
        return dict(name="John Carter", title='officer', status='missing')

class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_simple_jsonification(self):
        resp = self.app.get('/json')
        print resp.body
        assert '{"a": "hello world", "b": true}' in resp.body

    def test_custom_jsonification(self):
        resp = self.app.get('/custom')
        assert "wo-hoo!" in resp.body
