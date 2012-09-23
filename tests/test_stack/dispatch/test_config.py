import os
from tests.test_stack import TestConfig
from webtest import TestApp

def setup_noDB():
    global_config = {'debug': 'true', 
                     'error_email_from': 'paste@localhost', 
                     'smtp_server': 'localhost'}
    
    base_config = TestConfig(folder = 'config', 
                             values = {'use_sqlalchemy': False,
                                       'use_toscawidgets':False,
                                       'use_toscawidgets2':False}
                             )
                             
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app 

def test_basic_stack():
    app = setup_noDB()
    resp = app.get('/')
    assert resp.body.decode('ascii') == "my foo"

def test_config_reading():
    """Ensure that the config object can be read via dict and attr access"""
    app = setup_noDB()
    resp = app.get('/config_test')
    assert "default_renderer" in str(resp.body)
    resp = app.get('/config_attr_lookup')
    assert "genshi" in str(resp.body)
    resp = app.get('/config_dotted_values')
    assert "root" in str(resp.body)

def test_config_writing():
    """Ensure that new values can be added to the config object"""
    app = setup_noDB()
    value = "gooberblue"
    resp = app.get('/config_attr_set/'+value)
    assert value in str(resp.body)
    resp = app.get('/config_dict_set/'+value)
    assert value in str(resp.body)

