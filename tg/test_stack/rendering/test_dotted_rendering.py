from tg.test_stack import TestConfig, app_from_config
from tg.util import Bunch
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
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/index_dotted')
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_dotted')
    assert "Inheritance template" in resp
    assert "Master template" in resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index_dotted')
    print resp
    assert "<p>This is the mako index page</p>" in resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits_dotted')
    print resp
    assert "inherited mako page" in resp
    assert "Inside parent template" in resp

