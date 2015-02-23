# -*- coding: utf-8 -*-

""" Test cases for TG caching.  See:

http://turbogears.org/2.1/docs/main/Caching.html

For more details.
"""


import tg
from tg.controllers import TGController
from tg.decorators import expose, cached
from tg.caching import create_cache_key, cached_property, beaker_cache
from tg.controllers.util import etag_cache
from tg import cache
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

class TestCachedProperty(object):
    def setup(self):
        class FakeObject(object):
            def __init__(self):
                self.v = 0

            @cached_property
            def value(self):
                self.v += 1
                return self.v

        self.FakeObjectClass = FakeObject

    def test_cached_property(self):
        o = self.FakeObjectClass()
        for i in range(10):
            assert o.value == 1

    def test_cached_property_on_class(self):
        assert isinstance(self.FakeObjectClass.value, cached_property)

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
        assert resp.body.decode('ascii') == 'cached foo'
        resp = self.app.get('/simple/', params={'a':'bar'})
        assert resp.body.decode('ascii') == 'cached bar'
        resp = self.app.get('/simple/', params={'a':'baz'})
        assert resp.body.decode('ascii') == 'cached baz'

    def test_expiry(self):
        """ test that values expire from a single cache key. """
        mocktime.set_time(0)
        resp = self.app.get('/expiry/', params={'a':'foo1'})
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(1)
        resp = self.app.get('/expiry/', params={'a':'foo2'})
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(200) # wind clock past expiry
        resp = self.app.get('/expiry/', params={'a':'foo2'})
        assert resp.body.decode('ascii') == 'cached foo2'

class DecoratorController(TGController):
    
    @cached(expire=100, type='memory')
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
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(1)
        mockdb['DecoratorController.simple'] = 'foo2'
        resp = self.app.get('/simple/')
        assert resp.body.decode('ascii') == 'cached foo1'
        mocktime.set_time(200)
        mockdb['DecoratorController.simple'] = 'foo2'
        resp = self.app.get('/simple/')
        assert resp.body.decode('ascii') == 'cached foo2'

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
    def test_prova(self):
        app = make_app(SessionTouchController, config_options={
            'i18n.no_session_touch': False,
            'i18n.enabled': True
        })
        assert 'ACCESSED' in app.get('/session_get')

    def test_avoid_touch(self):
        app = make_app(SessionTouchController, config_options={
            'i18n.no_session_touch': True,
            'i18n.enabled': True
        })
        assert 'NOTOUCH' in app.get('/session_get')


class CustomSessionController(TGController):
    @expose('json')
    def session_init(self):
        tg.session['counter'] = 0
        tg.session.save()

        get_session = tg.request.environ['beaker.get_session']
        other_sess = get_session()
        other_sess['counter'] = 0
        other_sess.save()

        return dict(session_id=other_sess.id)

    @expose('json')
    def session_get(self, session_id):
        tg.session['counter'] -= 1
        tg.session.save()

        get_session = tg.request.environ['beaker.get_session']
        other_sess = get_session(session_id)
        other_sess['counter'] +=1
        other_sess.save()

        return dict(tg_session_counter=tg.session['counter'],
                    other_session_counter=other_sess['counter'])


class TestMultipleSessions(TestWSGIController):
    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(CustomSessionController, config_options={
            'session.key': 'test_app'
        })

    def test_multiple_sessions_work(self):
        resp = self.app.get('/session_init')
        session_id = resp.json['session_id']

        counters = self.app.get('/session_get', dict(session_id=session_id)).json
        assert counters['tg_session_counter'] == -1, counters
        assert counters['other_session_counter'] == 1, counters

        counters = self.app.get('/session_get', dict(session_id=session_id)).json
        assert counters['tg_session_counter'] == -2, counters
        assert counters['other_session_counter'] == 2, counters


def disable_cache(wrapped):
    def wrapper(*args, **kws):
        tg.config['cache.enabled'] = False
        x = wrapped(*args, **kws)
        tg.config['cache.enabled'] = True
        return x
    return wrapper


class CachedController(TGController):
    CALL_COUNT = 0

    @expose()
    @cached(key=None)
    def none_key(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached()
    def no_options(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(key='arg')
    def specified_cache_key(self, arg):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(key=['arg1', 'arg2'])
    def specified_cache_key_args(self, arg1, arg2):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(query_args=True)
    def cache_with_args(self, arg):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @disable_cache
    @cached()
    def disabled_cache(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    def invalidate_on_startup(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT

    @expose()
    @cached(invalidate_on_startup=True)
    def invalidate_on_startup(self):
        CachedController.CALL_COUNT += 1
        return 'Counter=%s' % CachedController.CALL_COUNT


class BeakerCacheController(TGController):  # For backward compatibility
    CALL_COUNT = 0

    @expose()
    @beaker_cache(key=None)
    def none_key(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache()
    def no_options(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(key='arg')
    def specified_cache_key(self, arg):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(key=['arg1', 'arg2'])
    def specified_cache_key_args(self, arg1, arg2):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(query_args=True)
    def cache_with_args(self, arg):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @disable_cache
    @beaker_cache()
    def disabled_cache(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    def invalidate_on_startup(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT

    @expose()
    @beaker_cache(invalidate_on_startup=True)
    def invalidate_on_startup(self):
        BeakerCacheController.CALL_COUNT += 1
        return 'Counter=%s' % BeakerCacheController.CALL_COUNT


class TestCacheTouch(TestWSGIController):
    CACHED_CONTROLLER = CachedController

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(self.CACHED_CONTROLLER)

    def test_none_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/none_key')
        assert 'Counter=1' in r
        r = self.app.get('/none_key')
        assert 'Counter=1' in r

    def test_invalidate_on_startup(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=1' in r
        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=2' in r

    def test_no_options(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/no_options')
        assert 'Counter=1' in r
        r = self.app.get('/no_options')
        assert 'Counter=1' in r

    def test_specified_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r

    def test_specified_cache_key_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=z')
        assert 'Counter=2' in r

    def test_cache_with_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r
        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r

    def test_different_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=y')
        assert 'Counter=2' in r

    def test_cache_key_instance_method(self):
        class Something(object):
            def method(self, arg):
                return arg

        o = Something()
        namespace, key = create_cache_key(o.method)

        assert namespace == 'tests.test_caching.Something'
        assert key == 'method'

    def test_cache_key_function(self):
        def method(self, arg):
            return arg

        namespace, key = create_cache_key(method)

        assert namespace == 'tests.test_caching'
        assert key == 'method'

    def test_disable_cache(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/disabled_cache')
        assert 'Counter=1' in r
        r = self.app.get('/disabled_cache')
        assert 'Counter=2' in r


class TestBeakerCacheTouch(TestWSGIController):
    CACHED_CONTROLLER = BeakerCacheController

    def __init__(self, *args, **kargs):
        TestWSGIController.__init__(self, *args, **kargs)
        self.app = make_app(self.CACHED_CONTROLLER)

    def test_none_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/none_key')
        assert 'Counter=1' in r
        r = self.app.get('/none_key')
        assert 'Counter=1' in r

    def test_invalidate_on_startup(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=1' in r
        r = self.app.get('/invalidate_on_startup')
        assert 'Counter=2' in r

    def test_no_options(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/no_options')
        assert 'Counter=1' in r
        r = self.app.get('/no_options')
        assert 'Counter=1' in r

    def test_specified_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r

    def test_specified_cache_key_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=y')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key_args?arg1=x&arg2=z')
        assert 'Counter=2' in r

    def test_cache_with_args(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r
        r = self.app.get('/cache_with_args?arg=x')
        assert 'Counter=1' in r, r

    def test_different_cache_key(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/specified_cache_key?arg=x')
        assert 'Counter=1' in r
        r = self.app.get('/specified_cache_key?arg=y')
        assert 'Counter=2' in r

    def test_cache_key_instance_method(self):
        class Something(object):
            def method(self, arg):
                return arg

        o = Something()
        namespace, key = create_cache_key(o.method)

        assert namespace == 'tests.test_caching.Something'
        assert key == 'method'

    def test_cache_key_function(self):
        def method(self, arg):
            return arg

        namespace, key = create_cache_key(method)

        assert namespace == 'tests.test_caching'
        assert key == 'method'

    def test_disable_cache(self):
        self.CACHED_CONTROLLER.CALL_COUNT = 0

        r = self.app.get('/disabled_cache')
        assert 'Counter=1' in r
        r = self.app.get('/disabled_cache')
        assert 'Counter=2' in r
