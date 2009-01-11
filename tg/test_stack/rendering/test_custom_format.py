from tg.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp
from pylons import tmpl_context

def setup_noDB():
    base_config = TestConfig(folder = 'rendering', 
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       'use_dotted_templatenames': False,
                                       }
                             )
    return app_from_config(base_config)

def test_json_custom_format():
    app = setup_noDB()
    resp = app.get('/custom_format?format=json')
    assert resp.content_type == 'application/json'
    assert '"status": "ok"' in resp.body
    assert '"format": "json"' in resp.body
    
def test_xml_custom_format():
    app = setup_noDB()
    resp = app.get('/custom_format?format=xml')

    assert 'text/xml' in resp.content_type
    assert "<status>ok</status>" in resp.body
    assert "<format>xml</format>" in resp.body
    
def test_html_custom_format():
    app = setup_noDB()
    resp = app.get('/custom_format?format=html')
    assert 'text/html' in resp.content_type
    assert "<li>Status: ok</li>" in resp.body
    assert "<li>Format: html</li>" in resp.body
