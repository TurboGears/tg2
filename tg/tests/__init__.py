import os
from unittest import TestCase
from xmlrpclib import loads, dumps

import pylons
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from pylons.util import ContextObj
from routes import request_config

data_dir = os.path.dirname(os.path.abspath(__file__))

try:
    shutil.rmtree(data_dir)
except:
    pass

class TestWSGIController(TestCase):
    def setUp(self):
        self.environ = {'pylons.routes_dict':dict(action='index'),
                        'paste.config':dict(global_conf=dict(debug=True))}
        pylons.c._push_object(ContextObj())

    def tearDown(self):
        pylons.c._pop_object()
    
    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.post(url, extra_environ=self.environ, params=kargs)
    
    def xmlreq(self, method, args=None):
        if args is None:
            args = ()
        ee = dict(CONTENT_TYPE='text/xml')
        data = dumps(args, methodname=method)
        self.response = response = self.app.post('/', params = data, extra_environ=ee)
        return loads(response.body)[0][0]
    

class ControllerWrap(object):
    def __init__(self, controller):
        self.controller = controller

    def __call__(self, environ, start_response):
        app = self.controller()
        app.start_response = None
        return app(environ, start_response)

class SetupCacheGlobal(object):
    def __init__(self, app, environ, setup_g=True, setup_cache=False,
                 setup_session=False):
        if setup_g:
            g = type('G object', (object,), {})
            g.message = 'Hello'
            g.counter = 0
            g.pylons_config = type('App conf', (object,), {})
            g.pylons_config.app_conf = dict(cache_enabled='True')
            self.g = g
        self.app = app
        self.environ = environ
        self.setup_cache = setup_cache
        self.setup_session = setup_session
        self.setup_g = setup_g

    def __call__(self, environ, start_response):
        registry = environ['paste.registry']
        environ_config = environ.setdefault('pylons.environ_config', {})
        if self.setup_cache:
            registry.register(pylons.cache, environ['beaker.cache'])
            environ_config['cache'] = 'beaker.cache'
        if self.setup_session:
            registry.register(pylons.session, environ['beaker.session'])
            environ_config['session'] = 'beaker.session'
        if self.setup_g:
            registry.register(pylons.g, self.g)

        # Update the environ
        environ.update(self.environ)
        registry.register(pylons.request, WSGIRequest(environ))
        registry.register(pylons.response, WSGIResponse())
        return self.app(environ, start_response)