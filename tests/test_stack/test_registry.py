# (c) 2005 Ben Bangert
# This module is part of the Python Paste Project and is released under
# the MIT License: http://www.opensource.org/licenses/mit-license.php
import inspect
import asyncio
import pytest
from webtest import TestApp
from tg.support.registry import RegistryManager, StackedObjectProxy, DispatchingConfig
from tg.util import Bunch

regobj = StackedObjectProxy()
secondobj = StackedObjectProxy(default=dict(hi='people'))

def simpleapp(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return ['Hello world!\n'.encode('utf-8')]

def simpleapp_withregistry(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return [('Hello world!Value is %s\n' % regobj.keys()).encode('utf-8')]

def simpleapp_withregistry_default(environ, start_response):
    status = '200 OK'
    response_headers = [('Content-type','text/plain')]
    start_response(status, response_headers)
    return [('Hello world!Value is %s\n' % secondobj).encode('utf-8')]

class RegistryUsingApp(object):
    def __init__(self, var, value, raise_exc=False):
        self.var = var
        self.value = value
        self.raise_exc = raise_exc

    def __call__(self, environ, start_response):
        if 'paste.registry' in environ:
            environ['paste.registry'].register(self.var, self.value)
        if self.raise_exc:
            raise self.raise_exc
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return [('Hello world!\nThe variable is %s' % str(regobj)).encode('utf-8')]

class RegistryUsingIteratorApp(object):
    def __init__(self, var, value):
        self.var = var
        self.value = value

    def __call__(self, environ, start_response):
        if 'paste.registry' in environ:
            environ['paste.registry'].register(self.var, self.value)
        status = '200 OK'
        response_headers = [('Content-type','text/plain')]
        start_response(status, response_headers)
        return iter([('Hello world!\nThe variable is %s' % str(regobj)).encode('utf-8')])

class RegistryMiddleMan(object):
    def __init__(self, app, var, value, depth):
        self.app = app
        self.var = var
        self.value = value
        self.depth = depth

    def __call__(self, environ, start_response):
        if 'paste.registry' in environ:
            environ['paste.registry'].register(self.var, self.value)
        app_response = [('\nInserted by middleware!\nInsertValue at depth \
            %s is %s' % (self.depth, str(regobj))).encode('utf-8')]
        app_iter = None
        app_iter = self.app(environ, start_response)
        if type(app_iter) in (list, tuple):
            app_response.extend(app_iter)
        else:
            response = []
            for line in app_iter:
                response.append(line)
            if hasattr(app_iter, 'close'):
                app_iter.close()
            app_response.extend(response)
        app_response.extend([('\nAppended by middleware!\nAppendValue at \
            depth %s is %s' % (self.depth, str(regobj))).encode('utf-8')])
        return app_response

def test_stacked_object_dir():
    regobj._push_object({'hi':'people'})
    try:
        values = dir(regobj)
        assert 'hi' in repr(regobj)
    finally:
        regobj._pop_object()

    assert '_current_obj' in values
    assert 'pop' in values
    assert 'items' in values

def test_stacked_object_dir_fail():
    values = dir(regobj)
    assert '_current_obj' in values

    assert repr(regobj).startswith('<tg.support.registry.StackedObjectProxy')

def test_stacked_object_callable():
    class Callable(object):
        def __call__(self, w):
            return w

    regobj._push_object(Callable())
    try:
        assert regobj('HI') == 'HI'
    finally:
        regobj._pop_object()

def test_stacked_object_common_actions():
    regobj._push_object(Bunch({'hi':'people'}))
    try:
        regobj['hi'] = 'val'
        assert regobj['hi'] == 'val'

        keys = []
        for k in regobj:
            keys.append(k)
        assert keys == ['hi'], keys

        assert len(regobj) == 1

        assert 'hi' in regobj

        assert bool(regobj) == True

        del regobj['hi']
        assert regobj.get('hi') is None

        regobj.someattr = 'val'
        assert regobj.someattr == 'val'

        del regobj.someattr
        assert getattr(regobj, 'someattr', None) is None
    finally:
        regobj._pop_object()

def test_stacked_object_pop_something_else():
    with pytest.raises(AssertionError):
        o = Bunch({'hi':'people'})
        regobj._push_object(o)
        regobj._pop_object({'another':'object'})

def test_stacked_object_pop_never_registered():
    with pytest.raises(AssertionError):
        regobj._pop_object()

def test_stacked_object_stack():
    so = StackedObjectProxy()

    assert(len(so._object_stack()) == 0)
    so._push_object({'hi':'people'})
    assert(len(so._object_stack()) == 1)
    so._pop_object()
    assert(len(so._object_stack()) == 0)

def test_stacked_object_preserve_empty():
    so = StackedObjectProxy()
    so._preserve_object()

    so._push_object({'hi':'people'})
    so._pop_object()
    so._preserve_object()

def test_stacked_object_preserved():
    so = StackedObjectProxy()
    assert not so._is_preserved

    so._push_object({'hi':'people'})
    assert not so._is_preserved

    so._pop_object()
    assert not so._is_preserved

    so._push_object({'hi':'people'})
    so._preserve_object()
    assert so._is_preserved
    so._pop_object()


def test_stacked_object_inspect():
    if not hasattr(inspect, 'unwrap'):
        pytest.skip("unwrap unavailable")

    so = StackedObjectProxy()
    assert inspect.unwrap(so) is so


def test_stacked_object_iscoroutinefunction():
    so = StackedObjectProxy()
    assert not asyncio.iscoroutinefunction(so)


def test_simple():
    app = TestApp(simpleapp)
    response = app.get('/')
    assert 'Hello world' in response

def test_solo_registry():
    obj = {'hi':'people'}
    wsgiapp = RegistryUsingApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res

def test_registry_no_object_error():
    app = TestApp(simpleapp_withregistry)
    with pytest.raises(TypeError):
        app.get('/')

def test_with_default_object():
    app = TestApp(simpleapp_withregistry_default)
    res = app.get('/')
    assert 'Hello world' in res
    assert "Value is {'hi': 'people'}" in res

def test_double_registry():
    obj = {'hi':'people'}
    secondobj = {'bye':'friends'}
    wsgiapp = RegistryUsingApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    wsgiapp = RegistryMiddleMan(wsgiapp, regobj, secondobj, 0)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    assert "InsertValue at depth 0 is {'bye': 'friends'}" in res
    assert "AppendValue at depth 0 is {'bye': 'friends'}" in res

def test_really_deep_registry():
    keylist = ['fred', 'wilma', 'barney', 'homer', 'marge', 'bart', 'lisa',
               'maggie']
    valuelist = range(0, len(keylist))
    obj = {'hi':'people'}
    wsgiapp = RegistryUsingApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    for depth in valuelist:
        newobj = {keylist[depth]: depth}
        wsgiapp = RegistryMiddleMan(wsgiapp, regobj, newobj, depth)
        wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    for depth in valuelist:
        assert "InsertValue at depth %s is {'%s': %s}" %\
               (depth, keylist[depth], depth) in res
    for depth in valuelist:
        assert "AppendValue at depth %s is {'%s': %s}" %\
               (depth, keylist[depth], depth) in res

def test_iterating_response():
    obj = {'hi':'people'}
    secondobj = {'bye':'friends'}
    wsgiapp = RegistryUsingIteratorApp(regobj, obj)
    wsgiapp = RegistryManager(wsgiapp)
    wsgiapp = RegistryMiddleMan(wsgiapp, regobj, secondobj, 0)
    wsgiapp = RegistryManager(wsgiapp)
    app = TestApp(wsgiapp)
    res = app.get('/')
    assert 'Hello world' in res
    assert 'The variable is' in res
    assert "{'hi': 'people'}" in res
    assert "InsertValue at depth 0 is {'bye': 'friends'}" in res
    assert "AppendValue at depth 0 is {'bye': 'friends'}" in res

def test_registry_streaming():
    def app(environ, start_response):
        environ['paste.registry'].register(regobj, {'hi':'people'})
        for i in range(10):
            yield str(i)
    rm = RegistryManager(app, streaming=True)

    environ = {}

    res = []
    for x in rm(environ, None):
        res.append(int(x))
        assert len(regobj._object_stack())

    assert len(res) == 10
    assert not(regobj._object_stack())

def test_registry_streaming_exception():
    def app(environ, start_response):
        environ['paste.registry'].register(regobj, {'hi':'people'})
        for i in range(10):
            if i == 5:
                raise SystemError('Woah!')
            else:
                yield str(i)
    app_with_rm = RegistryManager(app, streaming=True, preserve_exceptions=True)
    environ = {}
    try:
        for x in app_with_rm(environ, None):
            assert len(regobj._object_stack())
    except SystemError:
        #check the object got preserved due to exception
        assert regobj._object_stack()
        regobj._pop_object()
    else:
        assert False


def test_registry_not_preserved_when_disabled():
    def app(environ, start_response):
        environ['paste.registry'].register(regobj, {'hi':'people'})
        environ['paste.registry'].preserve()
        return ['HI']

    app_with_rm = RegistryManager(app, streaming=False, preserve_exceptions=False)
    environ = {}

    app_with_rm(environ, None)

    # check the object are not preserved as preserve_exceptions is False
    assert not regobj._object_stack()


def test_registry_preserved_when_forcefuly_preserved():
    def app(environ, start_response):
        environ['paste.registry'].register(regobj, {'hi':'people'})
        environ['paste.registry'].preserve(force=True)
        return ['HI']

    app_with_rm = RegistryManager(app, streaming=False, preserve_exceptions=False)
    environ = {}

    app_with_rm(environ, None)

    # check the object are preserved as force=True was used
    assert regobj._object_stack()


def test_dispatch_config():
    conf = DispatchingConfig()
    conf.push_process_config({'key':'default'})
    conf.push_thread_config({'key':'value'})
    assert conf.current()['key'] == 'value'
    conf.pop_thread_config()
    assert conf.current()['key'] == 'default'

    try:
        conf.pop_process_config({'another':'one'})
        pop_failed = False
    except AssertionError:
        pop_failed = True
    assert pop_failed, 'It should have failed due to different config popped'

    try:
        conf.current()
        assert False, 'It should fail due to empty objects stack'
    except AttributeError:
        pass


def test_stacked_object_twice():
    d = {'hi':'people'}

    def app(environ, start_response):
        environ['paste.registry'].register(regobj, d)
        environ['paste.registry'].register(regobj, d)
        for i in range(3):
            yield str(i)

    rm = RegistryManager(app, streaming=True)

    environ = {}
    resp = rm(environ, None)
    for idx, x in enumerate(resp, 1):
        objproxy = list(environ['paste.registry'].reglist[-1].values())[0][0]
        if idx == 1:
            objproxy._pop_object()
        elif idx == 2:
            # Trying to pop again should fail,
            # because as we pushed twice the same object
            # there is actually only on on the stack
            try:
                objproxy._pop_object()
            except AssertionError as e:
                assert str(e) == 'No object has been registered for this thread'
            else:
                assert False, 'Should have failed'

            # Won't proceed further, as exhausting the iterator
            # will lead to a crash due to cleanup of the registry.
            break

    assert idx == 2

    try:
        next(resp)
    except:
        # Looping again will crash because we already popped
        # The registered object and cleanup will fail.
        pass
