# -*- coding: utf-8 -*-

import pylons
import tg
from tg.controllers import *
from tg.tests import TestWSGIController, make_app, create_request
from tg.exceptions import HTTPFound
from nose.tools import eq_

def test_create_request():
    environ = { 'SCRIPT_NAME' : '/xxx' }
    request = create_request('/', environ)
    eq_('http://localhost/xxx/hello', tg.request.relative_url('hello'))
    eq_('http://localhost/xxx', tg.request.application_url)

def test_basicurls():
    create_request('/')
    eq_('/foo', url('/foo'))
    eq_('foo/bar', url(["foo", "bar"]))
    assert url("/foo", bar=1, baz=2) in \
            ["/foo?bar=1&baz=2", "/foo?baz=2&bar=1"]
    assert url("/foo", dict(bar=1, baz=2)) in \
            ["/foo?bar=1&baz=2", "/foot?baz=2&bar=1"]
    assert url("/foo", dict(bar=1, baz=None)) == "/foo?bar=1"

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
    eq_(url('/', x=u'\N{LATIN SMALL LETTER A WITH GRAVE}'
        u'\N{LATIN SMALL LETTER E WITH GRAVE}'
        u'\N{LATIN SMALL LETTER I WITH GRAVE}'
        u'\N{LATIN SMALL LETTER O WITH GRAVE}'
        u'\N{LATIN SMALL LETTER U WITH GRAVE}'),
        '/?x=%C3%A0%C3%A8%C3%AC%C3%B2%C3%B9'
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

def test_url_doesnt_change_tgparams():
    params = {'spamm': 'eggs'}
    result = url('/foo', params, spamm='ham')
    eq_(params['spamm'], 'eggs')

def test_approotsWithPath():
    create_request('/coolsite/root/subthing', {'SCRIPT_NAME' : '/subthing'})
    pylons.config.update({"server.webpath":"/coolsite/root"})
    eq_("/coolsite/root/subthing/foo", url("/foo"))