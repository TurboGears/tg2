# -*- coding: utf-8 -*-
import os
from tg.test_stack import TestConfig, app_from_config
from webtest import TestApp
from nose.tools import eq_

import tg
def setup_noDB():
    base_config = TestConfig(folder = 'dispatch', 
                             values = {'use_sqlalchemy': False,
                             'ignore_parameters': ["ignore", "ignore_me"],
                             }
                             )
    return app_from_config(base_config) 


app = setup_noDB()

def test_tg_style_default():
    resp = app.get('/sdfaswdfsdfa') #random string should be caught by the default route
    assert 'Default' in resp.body

def test_url_encoded_param_passing():
    resp = app.get('/feed?feed=http%3A%2F%2Fdeanlandolt.com%2Ffeed%2Fatom%2F')
    assert "http://deanlandolt.com/feed/atom/" in resp.body

def test_tg_style_index():
    resp = app.get('/index/')
    assert 'hello' in resp.body, resp.body

def test_tg_style_subcontroller_index():
    resp = app.get('/sub/index')
    assert "sub index" in resp.body, resp.body

def test_tg_style_subcontroller_default():
    resp=app.get('/sub/bob/tim/joe')
    assert "bob" in resp.body, resp.body
    assert 'tim' in resp.body, resp.body
    assert 'joe' in resp.body, resp.body

def test_redirect_absolute():
    resp = app.get('/redirect_me?target=/')
    assert resp.status == "302 Found", resp.status
    assert 'http://localhost/' in resp.headers['location'], resp.body
    resp = resp.follow()
    assert 'hello world' in resp, resp

def test_redirect_relative():
    resp = app.get('/redirect_me?target=hello&name=abc')
    resp = resp.follow()
    assert'Hello abc' in resp, resp
    resp = app.get('/sub/redirect_me?target=hello&name=def')
    resp = resp.follow()
#    print resp
    assert'Why HELLO! def' in resp, resp
    resp = app.get('/sub/redirect_me?target=../hello&name=ghi')
#    print resp
    resp = resp.follow()
#    print resp
    assert'Hello ghi' in resp, resp

def test_redirect_external():
    resp = app.get('/redirect_me?target=http://example.com')
#    print resp
    assert resp.status == "302 Found" and dict(resp.headers)['location'] == 'http://example.com', resp

def test_redirect_param():
    resp = app.get('/redirect_me?target=/hello&name=paj')
    print resp
    resp = resp.follow()
    assert'Hello paj' in resp
    resp = app.get('/redirect_me?target=/hello&name=pbj')
    print resp
    resp = resp.follow()
    assert'Hello pbj' in resp
    resp = app.get('/redirect_me?target=/hello&silly=billy&name=pcj')
    print resp
    resp = resp.follow()
    print resp
    assert'Hello pcj' in resp

def test_redirect_cookie():
    resp = app.get('/redirect_cookie?name=stefanha').follow()
    assert'Hello stefanha' in resp

def test_subcontroller_redirect_subindex():
    resp=app.get('/sub/redirect_sub').follow()
    assert'sub index' in resp

def test_subcontroller_redirect_sub2index():
    resp=app.get('/sub2/').follow()
    assert'hello list' in resp

#this test does not run because of some bug in nose
def _test_subcontroller_lookup():
    resp=app.get('/sub2/findme').follow()
    assert'lookup' in resp


def test_subcontroller_redirect_no_slash_sub2index():
    resp=app.get('/sub2/').follow()
    assert'hello list' in resp
    
def test_redirect_to_list_of_strings():
    resp = app.get('/sub/redirect_list').follow()
    print resp
    assert 'hello list' in resp

def test_flash_redirect():
    resp = app.get('/flash_redirect').follow()
    assert'Wow, flash!' in resp

def test_flash_no_redirect():
    resp = app.get('/flash_no_redirect')
    assert'Wow, flash!' in resp

def test_flash_unicode():
    resp = app.get('/flash_unicode').follow()
    content = resp.body.decode('utf8')
    assert u'Привет, мир!' in content

def test_flash_status():
    resp = app.get('/flash_status')
    assert 'ok' in resp

def test_tg_format_param():
    resp = app.get('/stacked_expose/?tg_format=application/json')
    assert '{"got_json' in resp.body

def test_custom_content_type():
    resp = app.get('/custom_content_type')
    assert 'image/png' == dict(resp.headers)['Content-Type'], resp
    assert resp.body == 'PNG', resp

def test_custom_text_plain_content_type():
    resp = app.get('/custom_content_text_plain_type')
    assert 'text/plain; charset=utf-8' == dict(resp.headers)['Content-Type'], resp
    assert resp.body == """a<br/>bx""", resp

def test_custom_content_type2():
    resp = app.get('/custom_content_type2')
    assert 'image/png' == dict(resp.headers)['Content-Type'], resp
    assert resp.body == 'PNG2', resp

def test_basicurls():
    resp = app.get("/test_url_sop")
    
def test_ignore_parameters():
    resp = app.get("/check_params?ignore='bar'&ignore_me='foo'")
    assert "None Recieved", resp.body
