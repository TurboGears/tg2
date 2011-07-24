# -*- coding: utf-8 -*-

""" Test cases for Pylons caching.  See:

http://wiki.pylonshq.com/display/pylonsdocs/Caching+in+Templates+and+Controllers

For more details.
"""


import tg
from tg.controllers import TGController
from tg.decorators import expose
from pylons.decorators.cache import beaker_cache
from pylons.controllers.util import etag_cache
from pylons import cache
from routes import Mapper
import pylons
from routes.middleware import RoutesMiddleware
from webob.exc import HTTPNotModified
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir

def setup():
    setup_session_dir()
    
def teardown():
    teardown_session_dir()

# a variable used to represent state held outside the controllers
mockdb = {}

class MockTime:
    
    """ A very simple class to mock the time module. This lets us slide time
    around to fake expiry in beaker.container. """
    
    mock_time = 0
    
    def time(self):
        return self.mock_time
    
    def set_time(self, v):
        self.mock_time = v

mocktime = MockTime()
import beaker.container
beaker.container.time = mocktime

class SimpleCachingController(TGController):
    
    """ Pylons supports a mechanism for arbitrary caches that can be allocated
    within controllers. Each cache value has a creation function associated
    with it that is called to retrieve it's results. """
    
    @expose()
    def simple(self, a):
        c = cache.get_cache("BasicTGController.index")
        x = c.get_value(key=a, 
                        createfunc=lambda: "cached %s" % a,
                        type="memory",
                        expiretime=3600)
        return x
    
    def createfunc(self):
        return "cached %s" % mockdb['expiry']
    
    @expose()
    def expiry(self, a):
        mockdb['expiry'] = a # inject a value into the context
        c = cache.get_cache("BasicTGController.index")
        x = c.get_value(key='test', 
                        createfunc=self.createfunc,
                        type="memory",
                        expiretime=100)
        return x

class TestSimpleCaching(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        self.app = make_app(SimpleCachingController, self.baseenviron)

    def test_simple_cache(self):
        """ test that caches get different results for different cache keys. """
        resp = self.app.get('/simple/', params={'a':'foo'})
        assert resp.body == 'cached foo'
        resp = self.app.get('/simple/', params={'a':'bar'})
        assert resp.body == 'cached bar'
        resp = self.app.get('/simple/', params={'a':'baz'})
        assert resp.body == 'cached baz'

    def test_expiry(self):
        """ test that values expire from a single cache key. """
        mocktime.set_time(0)
        resp = self.app.get('/expiry/', params={'a':'foo1'})
        assert resp.body == 'cached foo1'
        mocktime.set_time(1)
        resp = self.app.get('/expiry/', params={'a':'foo2'})
        assert resp.body == 'cached foo1'
        mocktime.set_time(200) # wind clock past expiry
        resp = self.app.get('/expiry/', params={'a':'foo2'})
        assert resp.body == 'cached foo2'

class DecoratorController(TGController):
    
    @beaker_cache(expire=100, type='memory')
    @expose()
    def simple(self):
        return "cached %s" % mockdb['DecoratorController.simple']
    
class TestDecoratorCaching(TestWSGIController):
    
    """ Test that the decorators function. """
    
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.baseenviron = {}
        self.app = make_app(DecoratorController, self.baseenviron)
    
    def test_simple(self):
        """ Test expiry of cached results for decorated functions. """
        mocktime.set_time(0)
        mockdb['DecoratorController.simple'] = 'foo1'
        resp = self.app.get('/simple/')
        assert resp.body == 'cached foo1'
        mocktime.set_time(1)
        mockdb['DecoratorController.simple'] = 'foo2'
        resp = self.app.get('/simple/')
        assert resp.body == 'cached foo1'
        mocktime.set_time(200)
        mockdb['DecoratorController.simple'] = 'foo2'
        resp = self.app.get('/simple/')
        assert resp.body == 'cached foo2'

class EtagController(TGController):

    @expose()
    def etagged(self, etag):
        etag_cache(etag)
        return "bar"
    
class TestEtagCaching(TestWSGIController):
    
    """ A simple mechanism is provided to set the etag header for returned results. """
    
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(EtagController)

    def test_etags(self):
        """ Test that the etag in the response headers is the one we expect. """
        resp = self.app.get('/etagged/', params={'etag':'foo'})
        assert resp.etag == 'foo', resp.etag
        resp = self.app.get('/etagged/', params={'etag':'bar'})
        assert resp.etag == 'bar', resp.etag    
        
    def test_304(self):
        resp = self.app.get('/etagged/', params={'etag':'foo'}, headers={'if-none-match': '"foo"'})
        assert "304" in resp.status, resp


class SessionTouchController(TGController):
    @expose()
    def session_get(self):
        if tg.session.accessed():
            return 'ACCESSED'
        else:
            return 'NOTOUCH'

class TestSessionTouch(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(SessionTouchController)

    def test_prova(self):
        tg.config['beaker.session.tg_avoid_touch'] = False
        assert 'ACCESSED' in self.app.get('/session_get')

    def test_avoid_touch(self):
        tg.config['beaker.session.tg_avoid_touch'] = True
        assert 'NOTOUCH' in self.app.get('/session_get')

