import os
from tests.test_stack import TestConfig, app_from_config
from webtest import TestApp

def setup_noDB():
    base_config = TestConfig(folder = 'config',
                             values = {'use_sqlalchemy': False,
                                       'pylons.tmpl_context_attach_args': False
                                       }
                             )
    return app_from_config(base_config)

def test_basic_stack():
    app = setup_noDB()
    resp = app.get('/')
    assert resp.body == "my foo"

def test_config_reading():
    """Ensure that the config object can be read via dict and attr access"""
    app = setup_noDB()
    resp = app.get('/config_test')
    assert "default_renderer" in resp.body
    resp = app.get('/config_attr_lookup')
    assert "genshi" in resp.body
    resp = app.get('/config_dotted_values')
    assert "environ_config" in resp.body

def test_config_writing():
    """Ensure that new values can be added to the config object"""
    app = setup_noDB()
    value = "gooberblue"
    resp = app.get('/config_attr_set/'+value)
    assert value in resp.body
    resp = app.get('/config_dict_set/'+value)
    assert value in resp.body

