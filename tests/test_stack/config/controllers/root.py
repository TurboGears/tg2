"""Main Controller"""

from tg import expose, redirect, config
from tg.controllers import TGController

class RootController(TGController):
    @expose()
    def index(self):
        return "my foo"

    @expose()
    def config_test(self):
        return str(config)
    
    @expose()
    def config_attr_lookup(self):
        return str(config.render_functions)
    
    @expose()
    def config_dotted_values(self):
        return str(config.paths)
    
    @expose()
    def config_attr_set(self, foo):
        config.test_value = foo
        return str(config.test_value)
        
    @expose()
    def config_set_method(self):
        return str(config.get('pylons'))

    @expose()
    def config_dict_set(self, foo):
        config['test_value'] = foo
        return str(config.test_value)
        

