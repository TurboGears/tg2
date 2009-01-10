from tg.test_stack import TestConfig
from tg.util import Bunch
from webtest import TestApp
from pylons import tmpl_context

def setup_noDB():
    global_config = {'debug': 'true', 
                     'error_email_from': 'paste@localhost', 
                     'smtp_server': 'localhost'}
    
    base_config = TestConfig(folder = 'rendering', 
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       }
                             )
                             
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app 

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

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index')
    print resp
    assert "<p>This is the mako index page</p>" in resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits')
    print resp
    assert "inherited mako page" in resp
    assert "Inside parent template" in resp
