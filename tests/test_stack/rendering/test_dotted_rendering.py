from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch, no_warn
from webtest import TestApp
from pylons import tmpl_context

def setup_noDB():
    base_config = TestConfig(folder = 'rendering',
                     values = {'use_sqlalchemy': False,
                               'pylons.helpers': Bunch(),
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': True,
                               }
                             )
    return app_from_config(base_config)

def test_default_chameleon_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/chameleon_index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_default_kajiki_renderer():
    app = setup_noDB()
    resp = app.get('/kajiki_index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_jinja_dotted():
    app = setup_noDB()
    resp = app.get('/jinja_dotted')
    assert "move along, nothing to see here" in resp, resp

def test_jinja_inherits_dotted():
    app = setup_noDB()
    resp = app.get('/jinja_inherits_dotted')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_inherits_mixed():
    # Mixed notation, dotted and regular
    app = setup_noDB()
    resp = app.get('/jinja_inherits_mixed')
    assert "Welcome on my awsome homepage" in resp, resp

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_dotted')
    assert "Inheritance template" in resp, resp
    assert "Master template" in resp, resp
 
def test_genshi_sub_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_dotted')
    assert "Inheritance template" in resp, resp
    assert "Master template" in resp, resp
    assert "from sub-template: sub.tobeincluded" in resp, resp

def test_genshi_sub_inheritance_frombottom():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_dotted_from_bottom')
    assert "Master template" in resp, resp
    assert "from sub-template: sub.frombottom_dotted" in resp, resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index_dotted')
    assert "<p>This is the mako index page</p>" in resp, resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits_dotted')
    assert "inherited mako page" in resp, resp
    assert "Inside parent template" in resp, resp

