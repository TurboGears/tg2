from tg.test_stack import TestConfig
from tg.util import Bunch
from paste.fixture import TestApp
from pylons import tmpl_context

def setup_noDB():
    global_config = {'debug': 'true', 
                     'error_email_from': 'paste@localhost', 
                     'smtp_server': 'localhost'}
    
    base_config = TestConfig(folder = 'rendering', 
                     values = {'use_sqlalchemy': False,
                               'pylons.helpers': Bunch(),
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': True,
                               }
                             )
                             
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app 

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

# the mako tests have been removed for the moment because the
# dotted name notation breaks inheritance support for Mako
def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index_dotted')
    print resp
    assert "<p>This is the mako index page</p>" in resp

"""
def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits_dotted')
    print resp
    assert "inherited mako page" in resp
    assert "Inside parent template" in resp
"""

