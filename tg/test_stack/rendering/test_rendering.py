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
                                       'use_legacy_renderer': False,
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
