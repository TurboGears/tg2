#!/usr/bin/python
from wsgiref.simple_server import make_server
import sys
import tg
from tg.configuration import AppConfig
from tg import TGController, expose

class AppGlobals(object):
    pass

class RootController(TGController):
    @expose()
    def index(self, *args, **kw):
        return 'HELLO FROM %s' % tg.request.path

app_config = AppConfig()
app_config.paths = {'root':'.', 'controllers':'.', 'static_files':'.', 'templates':[]}
app_config.disable_request_extensions = True
app_config.i18n_enabled = False
app_config.auto_reload_templates = False
app_config.use_transaction_manager = False
app_config.use_toscawidgets = False
app_config.package = sys.modules[__name__]
app_config['tg.app_globals'] = AppGlobals()
app_config['tg.root_controller'] = RootController()
app_config.init_config({}, {})

app = app_config.setup_tg_wsgi_app(lambda g,l:None)({}, full_stack=False)
make_server('', 8080, app).serve_forever()

