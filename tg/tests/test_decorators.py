# -*- coding: utf-8 -*-
import paste.httpexceptions as httpexceptions

import tg
import pylons
from tg.controllers import TGController
from tg.decorators import (
    expose,
    before_call,
    before_render,
    after_render,
    validate,
    before_validate,
    paginate,
    )


from formencode.validators import NotEmpty
from turbojson.jsonify import jsonify

from tg.tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir


def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

class MyClass(object):
    pass

@jsonify.when('isinstance(obj, MyClass)')
def jsonify_myclass(obj):
    return {'result':'wo-hoo!'}


HOOKS = []

def hook_factory(kind):

    def _hook(*args, **kwargs):
        global HOOKS
        HOOKS.append(kind)

    return _hook


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
    @expose('genshi:test', content_type='application/xml')
    def xml_or_json(self):
        return dict(name="John Carter", title='officer', status='missing')


    @expose()
    @before_call(hook_factory("before_call"))
    @before_render(hook_factory("before_render"))
    @after_render(hook_factory("after_render"))
    def hooks_are_called(self):
        return "ok"


    @expose()
    @before_validate(hook_factory("before_validate"))
    @validate(dict(foo=NotEmpty()), error_handler=hooks_are_called)
    def hooks_called_through_validation(self, foo=None):
        raise Exception("I'm not supposed to be called")



    @expose("genshi:tg.tests.paginate_test")
    @paginate("collection")
    def paginate_test(self, filter=None):
        collection = range(0, 100)
        if filter is not None:
            filter = int(filter)
            collection = [i for i in collection if i > filter]
        return dict(collection=collection)
    



class TestTGController(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(BasicTGController)

    def test_simple_jsonification(self):
        resp = self.app.get('/json')
        assert '{"a": "hello world", "b": true}' in resp.body

    def test_custom_jsonification(self):
        resp = self.app.get('/custom')
        assert "wo-hoo!" in resp.body

    def test_multi_dispatch_json(self):
        resp = self.app.get('/xml_or_json', headers={'accept':'application/json'})
        assert '''"status": "missing"''' in resp
        assert '''"name": "John Carter"''' in resp
        assert '''"title": "officer"''' in resp


    def test_before_call_before_render_after_render(self):
        global HOOKS
        HOOKS = []
        self.app.get("/hooks_are_called")
        assert "before_call" in HOOKS
        assert "before_render" in HOOKS
        assert "after_render" in HOOKS

        # now test that when the call is made implicit because
        # the action being a validation-error-handler,
        # the hooks are still called
        HOOKS = []

        self.app.get("/hooks_called_through_validation")
        assert "before_validate" in HOOKS
        assert "before_call" in HOOKS
        assert "before_render" in HOOKS
        assert "after_render" in HOOKS


    def test_pagination(self):
        res = self.app.get("/paginate_test")
        assert "/paginate_test?page=10" in res
        res = self.app.get("/paginate_test", params=dict(filter=50))
        assert "/paginate_test?filter=50&amp;page=5" in res
        
