# -*- coding: utf-8 -*-
from tests.test_stack import TestConfig, app_from_config
from tg.util import no_warn


def setup_noDB(html_flash=False):
    config = {'use_sqlalchemy': False,
              'use_toscawidgets': False,
              'use_toscawidgets2': False,
              'ignore_parameters': ["ignore", "ignore_me"]}

    if html_flash:
        config['flash.allow_html'] = True

    base_config = TestConfig(folder='dispatch',
                             values=config)
    return app_from_config(base_config)


@no_warn #should be _default now
def test_tg_style_default():
    app = setup_noDB()
    resp = app.get('/sdfaswdfsdfa') #random string should be caught by the default route
    assert 'Default' in resp.body.decode('utf-8')

def test_url_encoded_param_passing():
    app = setup_noDB()
    resp = app.get('/feed?feed=http%3A%2F%2Fdeanlandolt.com%2Ffeed%2Fatom%2F')
    assert "http://deanlandolt.com/feed/atom/" in resp.body.decode('utf-8')

def test_tg_style_index():
    app = setup_noDB()
    resp = app.get('/index/')
    assert 'hello' in resp.body.decode('utf-8'), resp

def test_tg_style_subcontroller_index():
    app = setup_noDB()
    resp = app.get('/sub/index')
    assert "sub index" in resp.body.decode('utf-8')

def test_tg_style_subcontroller_default():
    app = setup_noDB()
    resp=app.get('/sub/bob/tim/joe')
    assert 'bob' in resp.body.decode('utf-8'), resp
    assert 'tim' in resp.body.decode('utf-8'), resp
    assert 'joe' in resp.body.decode('utf-8'), resp

def test_redirect_absolute():
    app = setup_noDB()
    resp = app.get('/redirect_me?target=/')
    assert resp.status == "302 Found", resp.status
    assert 'http://localhost/' in resp.headers['location']
    resp = resp.follow()
    assert 'hello world' in resp, resp

@no_warn
def test_redirect_relative():
    app = setup_noDB()
    resp = app.get('/redirect_me?target=hello&name=abc')
    resp = resp.follow()
    assert 'Hello abc' in resp, resp
    resp = app.get('/sub/redirect_me?target=hello&name=def')
    resp = resp.follow()
    assert 'Why HELLO! def' in resp, resp
    resp = app.get('/sub/redirect_me?target=../hello&name=ghi')
    resp = resp.follow()
    assert 'Hello ghi' in resp, resp

def test_redirect_external():
    app = setup_noDB()
    resp = app.get('/redirect_me?target=http://example.com')
    assert resp.status == "302 Found" and resp.headers['location'] == 'http://example.com', resp

def test_redirect_param():
    app = setup_noDB()
    resp = app.get('/redirect_me?target=/hello&name=paj')
    resp = resp.follow()
    assert 'Hello paj' in resp, resp
    resp = app.get('/redirect_me?target=/hello&name=pbj')
    resp = resp.follow()
    assert 'Hello pbj' in resp, resp
    resp = app.get('/redirect_me?target=/hello&silly=billy&name=pcj')
    resp = resp.follow()
    assert 'Hello pcj' in resp, resp

def test_redirect_cookie():
    app = setup_noDB()
    resp = app.get('/redirect_cookie?name=stefanha').follow()
    assert 'Hello stefanha' in resp

def test_subcontroller_redirect_subindex():
    app = setup_noDB()
    resp=app.get('/sub/redirect_sub').follow()
    assert 'sub index' in resp

def test_subcontroller_redirect_sub2index():
    app = setup_noDB()
    resp=app.get('/sub2/').follow()
    assert 'hello list' in resp

#this test does not run because of some bug in nose
def _test_subcontroller_lookup():
    app = setup_noDB()
    resp=app.get('/sub2/findme').follow()
    assert 'lookup' in resp, resp

def test_subcontroller_redirect_no_slash_sub2index():
    app = setup_noDB()
    resp=app.get('/sub2/').follow()
    assert 'hello list' in resp, resp

def test_redirect_to_list_of_strings():
    app = setup_noDB()
    resp = app.get('/sub/redirect_list').follow()
    assert 'hello list' in resp, resp

def test_flash_redirect():
    app = setup_noDB()
    resp = app.get('/flash_redirect').follow()
    assert 'Wow, <br/>flash!' in resp, resp

def test_bigflash_redirect():
    app = setup_noDB()
    try:
        resp = app.get('/bigflash_redirect')
        assert False
    except Exception as e:
        assert 'Flash value is too long (cookie would be >4k)' in str(e)

def test_flash_no_redirect():
    app = setup_noDB()
    resp = app.get('/flash_no_redirect')
    assert 'Wow, flash!' in resp, resp

def test_flash_unicode():
    app = setup_noDB()
    resp = app.get('/flash_unicode').follow()
    content = resp.body.decode('utf8')
    assert str('Привет, мир!') in content, content

def test_flash_status():
    app = setup_noDB()
    resp = app.get('/flash_status')
    assert 'ok' in resp, resp

def test_flash_javascript():
    app = setup_noDB()
    resp = app.get('/flash_render?using_js=True')
    expected = 'webflash({"id": "flash", "name": "webflash"})'
    epxected_reverse = 'webflash({"name": "webflash", "id": "flash"})'
    assert expected in resp or epxected_reverse in resp, resp
    assert 'webflash.render()' in resp, resp

def test_flash_render_plain():
    app = setup_noDB()
    resp = app.get('/flash_render')
    assert 'JS &lt;br/&gt;Flash' in resp, resp

def test_flash_render_plain_with_html():
    app = setup_noDB(html_flash=True)
    resp = app.get('/flash_render')
    assert 'JS <br/>Flash' in resp, resp

def test_flash_render_no_message():
    app = setup_noDB()
    resp = app.get('/flash_render?with_message=False')
    assert 'flash' not in resp

def test_custom_content_type():
    app = setup_noDB()
    resp = app.get('/custom_content_type')
    assert 'image/png' == dict(resp.headers)['Content-Type'], resp
    assert resp.body.decode('utf-8') == 'PNG', resp

def test_custom_text_plain_content_type():
    app = setup_noDB()
    resp = app.get('/custom_content_text_plain_type')
    assert 'text/plain; charset=utf-8' == dict(resp.headers)['Content-Type'], resp
    assert resp.body.decode('utf-8') == """a<br/>bx""", resp

@no_warn
def test_custom_content_type2():
    app = setup_noDB()
    resp = app.get('/custom_content_type2')
    assert 'image/png' == dict(resp.headers)['Content-Type'], resp
    assert resp.body.decode('utf-8') == 'PNG2', resp

@no_warn
def test_basicurls():
    app = setup_noDB()
    resp = app.get("/test_url_sop")

def test_ignore_parameters():
    app = setup_noDB()
    resp = app.get("/check_params?ignore='bar'&ignore_me='foo'")
    assert "None recieved" in resp.text, resp.text

def test_https_redirect():
    app = setup_noDB()
    resp = app.get("/test_https?foo=bar&baz=bat")
    assert 'https://' in resp, resp
    assert resp.location.endswith("/test_https?foo=bar&baz=bat")
    resp = app.post("/test_https?foo=bar&baz=bat", status=405)

def test_return_non_string():
    app = setup_noDB()
    try:
        resp = app.get("/return_something")
        assert False
    except:
        # Do not try to be too smart catching all cases
        # if returned value is not a valid wsgi app_iter
        # let it crash
        pass

def test_return_none():
    app = setup_noDB()
    resp = app.get('/return_none', status=204)
    assert 'Content-Type' not in str(resp), resp

def test_return_modified_response():
    app = setup_noDB()
    resp = app.get('/return_modified_response', status=201)
    assert 'Hello World' in resp.text

class TestVisits(object):
    def test_visit_path_sub1(self):
        app = setup_noDB()
        resp = app.get("/sub/hitme")
        assert str(resp).endswith('/sub@/sub')

    def test_visit_path_nested(self):
        app = setup_noDB()
        resp = app.get("/sub/nested/hitme")
        assert str(resp).endswith('/sub/nested*/sub/nested')

    def test_visit_path_nested_index(self):
        app = setup_noDB()
        resp = app.get("/sub/nested")
        assert str(resp).endswith('/sub/nested-/sub/nested')

    def test_runtime_visit_path_subcontroller(self):
        app = setup_noDB()
        resp = app.get("/sub/nested/nested/hitme")
        assert str(resp).endswith('*/sub/nested')

    def test_runtime_visit_path(self):
        app = setup_noDB()
        resp = app.get("/sub/nested/hiddenhitme")
        assert str(resp).endswith(' /sub/nested')
