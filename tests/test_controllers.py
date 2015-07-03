# -*- coding: utf-8 -*-
import tg
from tg.controllers import *
from tg.exceptions import HTTPFound
from nose.tools import eq_
from tests.base import setup_session_dir, teardown_session_dir
from tg.util import no_warn
from tg.util.webtest import test_context
from tg._compat import u_, string_type

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

def test_create_request():
    with test_context(None, '/', { 'SCRIPT_NAME' : '/xxx' }):
        eq_('http://localhost/xxx/hello', tg.request.relative_url('hello'))
        eq_('http://localhost/xxx', tg.request.application_url)

def test_approots():
    with test_context(None, '/subthing/',{ 'SCRIPT_NAME' : '/subthing' }):
        eq_("foo", url("foo"))
        eq_("/subthing/foo", url("/foo"))

def test_lowerapproots():
    with test_context(None, '/subthing/subsubthing/',{ 'SCRIPT_NAME' : '/subthing/subsubthing' }):
        eq_("/subthing/subsubthing/foo", url("/foo"))


@no_warn
def test_multi_values():
    with test_context(None, '/'):
        r = url("/foo", params=dict(bar=("asdf", "qwer")))
        assert r in \
                ["/foo?bar=qwer&bar=asdf", "/foo?bar=asdf&bar=qwer"], r
        r = url("/foo", params=dict(bar=[1,2]))
        assert r in \
                ["/foo?bar=1&bar=2", "/foo?bar=2&bar=1"], r


@no_warn
def test_unicode():
    """url() can handle unicode parameters"""
    with test_context(None, '/'):
        unicodestring =  u_('àèìòù')
        eq_(url('/', params=dict(x=unicodestring)),
            '/?x=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'
            )


@no_warn
def test_list():
    """url() can handle list parameters, with unicode too"""
    with test_context(None, '/'):
        value = url('/', params=dict(foo=['bar', u_('à')])),
        assert '/?foo=bar&foo=%C3%A0' in value, value


@no_warn
def test_url_positional_params():
    with test_context(None, '/'):
        params = {'spamm': 'eggs'}
        result = url('/foo', params)
        assert 'spamm=eggs' in result

def test_url_with_params_key():
    with test_context(None, '/'):
        params = {'spamm': 'eggs'}
        result = url('/foo', params=params)
        assert 'spamm=eggs' in result

@no_warn
def test_url_strip_None():
    with test_context(None, '/'):
        params = {'spamm':'eggs', 'hamm':None }
        result = url('/foo', params=params)
        assert 'hamm' not in result, result

def test_lurl():
    with test_context(None, '/'):
        params = {'spamm':'eggs', 'hamm':None }
        assert url('/foo', params=params) == str(lurl('/foo', params=params))

@no_warn
def test_url_qualified():
    """url() can handle list parameters, with unicode too"""
    with test_context(None, '/'):
        value = url('/', qualified=True)
        assert value.startswith('http')

@no_warn
def test_lurl():
    """url() can handle list parameters, with unicode too"""
    with test_context(None, '/'):
        value = lurl('/lurl')
        assert not isinstance(value, string_type)
        assert value.startswith('/lurl')
        assert str(value) == repr(value) == value.id == value.encode('utf-8').decode('utf-8') == value.__html__()

def test_lurl_as_HTTPFound_location():
    with test_context(None, '/'):
        exc = HTTPFound(location=lurl('/lurl'))

        def _fake_start_response(*args, **kw):
            pass

        resp = exc({'PATH_INFO':'/',
                    'wsgi.url_scheme': 'HTTP',
                    'REQUEST_METHOD': 'GET',
                    'SERVER_NAME': 'localhost',
                    'SERVER_PORT': '80'}, _fake_start_response)
        assert b'resource was found at http://localhost:80/lurl' in resp[0]

def test_HTTPFound_without_location():
    exc = HTTPFound(add_slash=True)
 
    def _fake_start_response(*args, **kw):
        pass

    resp = exc({'PATH_INFO':'/here',
                'wsgi.url_scheme': 'HTTP',
                'REQUEST_METHOD': 'GET',
                'SERVER_NAME': 'localhost',
                'SERVER_PORT': '80'}, _fake_start_response)
    assert b'resource was found at http://localhost:80/here/' in resp[0]

@no_warn
def test_lurl_format():
    """url() can handle list parameters, with unicode too"""
    with test_context(None, '/'):
        value = lurl('/lurl/{0}')
        value = value.format('suburl')
        assert value == '/lurl/suburl', value

@no_warn
def test_lurl_add():
    """url() can handle list parameters, with unicode too"""
    with test_context(None, '/'):
        value = lurl('/lurl')
        value = value + '/suburl'
        assert value == '/lurl/suburl', value

@no_warn
def test_lurl_radd():
    """url() can handle list parameters, with unicode too"""
    with test_context(None, '/'):
        value = lurl('/lurl')
        value = '/suburl' + value
        assert value == '/suburl/lurl', value
