#!/usr/bin/python
from wsgiref.simple_server import make_server
import sys
from tg.configuration import AppConfig
from tg import TGController, expose

try:
    import pylons
    has_pylons = True
except:
    has_pylons = False

class AppGlobals(object):
    pass

app_config = AppConfig()
app_config.paths['root'] = app_config.paths['controllers'] = '.'
app_config.disable_request_extensions = True
app_config.i18n_enabled = False
app_config.auto_reload_templates = False
app_config.use_toscawidgets = False
app_config.package = sys.modules[__name__]
app_config['tg.app_globals'] = AppGlobals()
app_config['pylons.app_globals'] = AppGlobals()
app_config.init_config({}, {})

class RootController(TGController):
    @expose()
    def index(self, *args, **kw):
        return 'OK'

from paste.registry import RegistryManager
import tg
from tg import TGApp

class MyApp(TGApp):
    root_controller = RootController()

    def resolve(self, environ, start_response):
        if has_pylons:
            environ['pylons.routes_dict'] = {}
            environ['pylons.routes_dict']['action'] = 'routes_placeholder'

            registry = environ['paste.registry']
            registry.register(tg.session, None)
            registry.register

        return self.root_controller

app = RegistryManager(MyApp())

if len(sys.argv) > 1 and sys.argv[1] == '-t':
    from profile_middleware import ProfileMiddleware
    app = ProfileMiddleware(app)

make_server('', 8000, app).serve_forever()

