import tg
from tg import expose, validate
from tg.decorators import *
from paste.httpexceptions import *
from pylons.helpers import *
from datetime import datetime
from formencode.validators import *
from formencode import Schema

from turbojson.jsonify import jsonify

class MyClass: pass

@jsonify.when('isinstance(obj, MyClass)')
def jsonify_myclass(obj):
    return {'result':'wo-hoo!'}

def schema(d=None, **kw):
    dd = {}
    if d:
        dd.update(d)
    dd.update(**kw)
    return Schema.__metaclass__('schema', (Schema,), dd)

class MySubSubController:

    @expose()
    def foo(self):
        redirect_to('./bar')
        return 'SubSubFoo!\r\n'
        
    @expose()
    def bar(self, a, b, c):
        return 'REDIRECTED %s %s %s!\r\n' % (a,b,c)
        
class MySubController:

    sub = MySubSubController()

    @expose()
    def index(self):
        return 'SubIndex'

    @expose()
    def foo(self):
        return 'SubFoo!\r\n'


    @expose('kid:blogtutorial.templates.test')
    @validate(a=Int(), error_handler='../index')
    def do_test(self, a):
        print a
        return dict(current_time=datetime.now(),
                    a=repr(a))

class CoolSubController:

    def __init__(self, arg):
        self.arg = arg

    @expose('json')
    def index(self):
        return dict(arg=self.arg, method='index')

    @expose('json')
    def foo(self):
        return dict(arg=self.arg, method='foo')

    @expose('json')
    def default(self, *l):
        return dict(arg=self.arg, method='default', remainder=l)
        

def my_before_validate(*l, **kw):
    print 'running before_validate with %s,%s' % (l, kw)
    
def my_before_call(*l, **kw):
    print 'running before_call with %s,%s' % (l, kw)
    
def my_before_render(*l, **kw):
    print 'running before_render with %s,%s' % (l, kw)
    
def my_after_render(*l, **kw):
    print 'running after_render with %s,%s' % (l, kw)
    

class RootController(tg.TurboGearsController):

    sub=MySubController()

    @expose('kid:blogtutorial.templates.test_form')

    def index(self):
        return {}

    @expose('json')
    @expose('kid:blogtutorial.templates.test_form', content_type='text/html')
    def test_json(self):
        return dict(a=1, b=2, c=MyClass())

    @expose('kid:blogtutorial.templates.test')
    @before_validate(my_before_validate)
    @before_call(my_before_call)
    @before_render(my_before_render)
    @after_render(my_after_render)
    @validate(a=Int(), error_handler='./index')
    def do_test(self, a):
        return dict(current_time=datetime.now(),
                    a=repr(a))

    @expose()
    def lookup(self, arg, *remainder):
        return CoolSubController(arg), remainder
