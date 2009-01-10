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
                                       'use_dotted_templatenames': False,
                                       }
                             )
                             
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app
    
#
def test_json_custom_format():
    app = setup_noDB()
    resp = app.get('/custom_format?format=json')
    assert resp.header('Content-Type') == 'application/json; charset=utf-8'
    assert '"status": "ok"' in resp.body
    assert '"format": "json"' in resp.body
    
def test_xml_custom_format():
    app = setup_noDB()
    resp = app.get('/custom_format?format=xml')
    assert resp.header('Content-Type') == 'text/xml; charset=utf-8'
    assert "<status>ok</status>" in resp.body
    assert "<format>xml</format>" in resp.body
    
def test_html_custom_format():
    app = setup_noDB()
    resp = app.get('/custom_format?format=html')
    assert resp.header('Content-Type') == 'text/html; charset=utf-8'
    assert "<li>Status: ok</li>" in resp.body
    assert "<li>Format: html</li>" in resp.body
