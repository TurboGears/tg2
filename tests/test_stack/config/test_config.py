from tests.test_stack import TestConfig, app_from_config

def setup_noDB():
    base_config = TestConfig(folder = 'config',
                             values = {'use_sqlalchemy': False,
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2':False}
                             )
    return app_from_config(base_config)

def test_basic_stack():
    app = setup_noDB()
    resp = app.get('/')
    assert resp.body.decode('ascii') == "my foo"

def test_config_reading():
    """Ensure that the config object can be read via dict and attr access"""
    app = setup_noDB()
    resp = app.get('/config_test')
    resp_body = resp.body.decode('ascii')

    assert "default_renderer" in resp_body
    resp = app.get('/config_attr_lookup')
    assert "genshi" in resp_body
    resp = app.get('/config_dotted_values')
    assert "root" in resp_body

def test_config_writing():
    """Ensure that new values can be added to the config object"""
    app = setup_noDB()
    value = "gooberblue"
    resp = app.get('/config_attr_set/'+value)
    resp_body = resp.body.decode('ascii')

    assert value in resp_body
    resp = app.get('/config_dict_set/'+value)
    assert value in resp_body

