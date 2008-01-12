# -*- coding: utf-8 -*-
import paste.httpexceptions as httpexceptions

import tg
import pylons
from tg.controllers import TurboGearsController
from pylons.decorators import expose

from turbojson.jsonify import jsonify

from tg.tests import TestWSGIController, make_app

pylons.buffet = pylons.templating.Buffet(default_engine='genshi')
class MyClass(object):
    pass

@jsonify.when('isinstance(obj, MyClass)')
def jsonify_myclass(obj):
    return {'result':'wo-hoo!'}



class BasicTGController(TurboGearsController):

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
        self.baseenviron = {}
        self.app = make_app(self.baseenviron)

    def setUp(self):
        TestWSGIController.setUp(self)
        self.baseenviron.update(self.environ)

    def test_basic_json(self):
        pass

    def test_content_negotiation(self):
        pass
