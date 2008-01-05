import os
from unittest import TestCase
from xmlrpclib import loads, dumps

import pylons
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from pylons.util import ContextObj, PylonsContext
from pylons.testutil import ControllerWrap, SetupCacheGlobal
#import pylons.tests

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
