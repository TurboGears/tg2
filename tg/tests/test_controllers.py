# -*- coding: utf-8 -*-

import pylons
import tg
from tg.controllers import *
from tg.exceptions import HTTPFound
from nose.tools import eq_
from tg.tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request

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

def test_multi_values():
    create_request('/')
    assert url("/foo", bar=[1,2]) in \
            ["/foo?bar=1&bar=2", "/foo?bar=2&bar=1"]
    assert url("/foo", bar=("asdf","qwer")) in \
            ["/foo?bar=qwer&bar=asdf", "/foo?bar=asdf&bar=qwer"]

def test_unicode():
    """url() can handle unicode parameters"""
    create_request("/")
    unicodestring = (u'\N{LATIN SMALL LETTER A WITH GRAVE}'
        u'\N{LATIN SMALL LETTER E WITH GRAVE}'
        u'\N{LATIN SMALL LETTER I WITH GRAVE}'
        u'\N{LATIN SMALL LETTER O WITH GRAVE}'
        u'\N{LATIN SMALL LETTER U WITH GRAVE}')
    print unicodestring.encode('utf8')
    eq_(url('/', x=unicodestring),
        '/?x=%25C3%25A0%25C3%25A8%25C3%25AC%25C3%25B2%25C3%25B9'
        )

def test_list():
    """url() can handle list parameters, with unicode too"""
    create_request("/")
    eq_(
        url('/', foo=['bar', u'\N{LATIN SMALL LETTER A WITH GRAVE}']),
        '/?foo=bar&foo=%C3%A0'
    )

def test_url_kwargs_overwrite_tgparams():
    params = {'spamm': 'eggs'}
    result = url('/foo', params, spamm='ham')
    assert 'spamm=ham' in result

def test_url_with_params_key():
    params = {'spamm': 'eggs'}
    result = url('/foo', params=params, spamm='ham')
    assert 'spamm=eggs' in result

def test_url_doesnt_change_tgparams():
    params = {'spamm': 'eggs'}
    result = url('/foo', params, spamm='ham')
    eq_(params['spamm'], 'eggs')

#def test_approotsWithPath():
#    create_request('/coolsite/root/subthing/', {'SCRIPT_NAME' : '/subthing'})
#    pylons.config.update({"server.webpath":"/coolsite/root"})
#    eq_("/coolsite/root/subthing/foo", pylons.url("/foo"))