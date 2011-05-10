from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp
from pylons import tmpl_context

def setup_noDB():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'pylons.tmpl_context_attach_args': False

                                       }
                             )
    return app_from_config(base_config)

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/')
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits')
    assert "Inheritance template" in resp
    assert "Master template" in resp

def test_genshi_sub_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub')
    assert "Inheritance template" in resp
    assert "Master template" in resp
    assert "from sub-template: sub.tobeincluded" in resp

def test_genshi_sub_inheritance_from_bottom():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_from_bottom')
    assert "from sub-template: sub.frombottom" in resp
    assert "Master template" in resp

def test_chameleon_genshi_base():
    app = setup_noDB()
    resp = app.get('/chameleon_genshi_index')
    assert "<p>TurboGears 2 is rapid web application development toolkit designed to make your life easier.</p>" in resp

def test_chameleon_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/chameleon_genshi_inherits')
    assert "Inheritance template" in resp
    assert "Master template" in resp

def _test_jinja_inherits():
    app = setup_noDB()
    resp = app.get('/jinja_inherits')
    assert "Welcome on my awsome homepage" in resp, resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index')
    assert "<p>This is the mako index page</p>" in resp, resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits')
    assert "inherited mako page" in resp, resp
    assert "Inside parent template" in resp, resp

def test_template_override():
#    app = setup_noDB()
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['genshi']
                                       }
                             )
    app = app_from_config(base_config)
    r =app.get('/template_override')
    assert "Not overridden" in r, r
    r = app.get('/template_override', params=dict(override=True))
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override')
    assert "Not overridden" in r, r

def test_template_override_wts():
#    app = setup_noDB()
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['genshi']
                                       }
                             )
    app = app_from_config(base_config)
    r = app.get('/template_override_wts', status=302) # ensure with_trailing_slash
    r =app.get('/template_override_wts/')
    assert "Not overridden" in r, r
    r = app.get('/template_override_wts/', params=dict(override=True))
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override_wts/')
    assert "Not overridden" in r, r

def test_template_override_content_type():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['mako', 'genshi']
                                       }
                             )
    app = app_from_config(base_config)
    r =app.get('/template_override_content_type')
    assert r.content_type == 'text/javascript'
    assert "Not overridden" in r, r
    r = app.get('/template_override_content_type', params=dict(override=True))
    assert r.content_type == 'text/javascript'
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override_content_type')
    assert "Not overridden" in r, r

def test_template_custom_format_default():
    app = setup_noDB()
    resp = app.get('/custom_format')
    assert 'OK' in resp
    assert resp.content_type == 'text/html'

def test_template_custom_format_xml():
    app = setup_noDB()
    resp = app.get('/custom_format?format=xml')
    assert 'xml' in resp
    assert resp.content_type == 'text/xml'

def test_template_custom_format_json():
    app = setup_noDB()
    resp = app.get('/custom_format?format=json')
    assert 'json' in resp
    assert resp.content_type == 'application/json'

def test_template_custom_format_html():
    app = setup_noDB()
    resp = app.get('/custom_format?format=html')
    assert 'html' in resp
    assert resp.content_type == 'text/html'