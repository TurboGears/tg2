import os
import tg 

from tg.configuration import AppConfig
from paste.fixture import TestApp

class TestConfig(AppConfig):

    def __init__(self, values=None):
        
        if not values:
            self.renderers = ['genshi'] 
            self.render_functions = tg.util.Bunch()
            self.package = tg.tests.test_stack
            self.default_renderer = 'genshi'
            self.globals = self
            self.helpers = {}
            self.auth_backend = None
            self.auto_reload_templates = False
            self.use_legacy_renderer = True
            self.serve_static = False

        else: 
            for key, value in values.items():
                setattr(self, key, value)

        root = "."
        test_base_path = os.path.join(root,'tg', 'tests', 'test_stack',)
        test_config_path = os.path.join(test_base_path, 'config')
        print test_config_path
        self.paths=tg.util.Bunch(
                    root=test_base_path,
                    controllers=os.path.join(test_config_path, 'controllers'),
                    static_files=os.path.join(test_config_path, 'public'),
                    templates=[os.path.join(test_config_path, 'templates')]
                    )
        
    def setup_helpers_and_globals(self):
        tg.config['pylons.app_globals'] = self.globals
        tg.config['pylons.h'] = self.helpers
        
def setup_noDB():
    global_config = {'debug': 'true', 
                     'error_email_from': 'paste@localhost', 
                     'smtp_server': 'localhost'}
    
    base_config = TestConfig()
    base_config.use_sqlalchemy = False
    env_loader = base_config.make_load_environment()
    app_maker = base_config.setup_tg_wsgi_app(env_loader)
    app = TestApp(app_maker(global_config, full_stack=True))
    return app 

def test_basic_stack():
    app = setup_noDB()
    resp = app.get('/')
    assert resp.body == "my foo"

def test_config_reading():
    app = setup_noDB()
    resp = app.get('/config_test')
    assert "default_renderer" in resp.body
    resp = app.get('/config_attr_lookup')
    assert "genshi" in resp.body
    resp = app.get('/config_dotted_values')
    assert "environ_config" in resp.body

def test_config_writing():
    app = setup_noDB()
    value = "gooberblue"
    resp = app.get('/config_attr_set/'+value)
    assert value in resp.body
    resp = app.get('/config_dict_set/'+value)
    assert value in resp.body
    
    
    






