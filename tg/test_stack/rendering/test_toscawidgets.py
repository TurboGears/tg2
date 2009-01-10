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
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': False,
                               }
                             )
                             
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app 


expected_field = """<input type="text" name="year" class="textfield" id="movie_form_year" value="" size="4" />"""

def test_basic_form_rendering():
    app = setup_noDB()
    resp = app.get('/form')
    print resp.body
    assert "form" in resp
    assert expected_field in resp


