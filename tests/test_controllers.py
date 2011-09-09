# -*- coding: utf-8 -*-

import pylons
import tg
from tg.controllers import *
from tg.exceptions import HTTPFound
from nose.tools import eq_
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request
from tg.util import no_warn

def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

def test_create_request():
    environ = { 'SCRIPT_NAME' : '/xxx' }
    request = create_request('/', environ)
    eq_('http://localhost/xxx/hello', tg.request.relative_url('hello'))
    eq_('http://localhost/xxx', tg.request.application_url)

def test_approots():
    create_request('/subthing/',{ 'SCRIPT_NAME' : '/subthing' })
    eq_("foo", url("foo"))
    eq_("/subthing/foo", url("/foo"))

def test_lowerapproots():
    create_request(
                '/subthing/subsubthing/',
                { 'SCRIPT_NAME' : '/subthing/subsubthing' }
                )
    eq_("/subthing/subsubthing/foo", url("/foo"))

@no_warn
def test_multi_values():
    create_request('/')
    r = url("/foo", bar=(u"asdf",u"qwer"))
    assert r in \
            ["/foo?bar=qwer&bar=asdf", "/foo?bar=asdf&bar=qwer"], r
    r = url("/foo", bar=[1,2])
    assert  r in \
            ["/foo?bar=1&bar=2", "/foo?bar=2&bar=1"], r

@no_warn
def test_unicode():
    """url() can handle unicode parameters"""
    create_request("/")
    unicodestring = (u'\N{LATIN SMALL LETTER A WITH GRAVE}'
        u'\N{LATIN SMALL LETTER E WITH GRAVE}'
        u'\N{LATIN SMALL LETTER I WITH GRAVE}'
        u'\N{LATIN SMALL LETTER O WITH GRAVE}'
        u'\N{LATIN SMALL LETTER U WITH GRAVE}')
    eq_(url('/', x=unicodestring),
        '/?x=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'
        )

@no_warn
def test_list():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    value = url('/', foo=['bar', u'\N{LATIN SMALL LETTER A WITH GRAVE}']),
    assert '/?foo=bar&foo=%C3%A0' in value, value

@no_warn
def test_url_kwargs_overwrite_tgparams():
    params = {'spamm': 'eggs'}
    result = url('/foo', params, spamm='ham')
    assert 'spamm=ham' in result

def test_url_with_params_key():
    params = {'spamm': 'eggs'}
    result = url('/foo', params=params)
    assert 'spamm=eggs' in result

@no_warn
def test_url_strip_None():
    params = {'spamm':'eggs', 'hamm':None }
    result = url('/foo', params=params)
    assert 'hamm' not in result, result

@no_warn
def test_url_doesnt_change_tgparams():
    params = {'spamm': 'eggs'}
    result = url('/foo', params, spamm='ham')
    eq_(params['spamm'], 'eggs')

def test_lurl():
    params = {'spamm':'eggs', 'hamm':None }
    assert url('/foo', params=params) == str(lurl('/foo', params=params))

#def test_approotsWithPath():
#    create_request('/coolsite/root/subthing/', {'SCRIPT_NAME' : '/subthing'})
#    pylons.config.update({"server.webpath":"/coolsite/root"})
#    eq_("/coolsite/root/subthing/foo", pylons.url("/foo"))
