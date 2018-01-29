# -*- coding: utf-8 -*-

import os, shutil
from unittest import TestCase
from tg.appwrappers.caching import CacheApplicationWrapper
from tg.appwrappers.errorpage import ErrorPageApplicationWrapper
from tg.appwrappers.i18n import I18NApplicationWrapper
from tg.appwrappers.identity import IdentityApplicationWrapper
from tg.appwrappers.session import SessionApplicationWrapper
from tg.configuration.utils import DependenciesList

try:
    from xmlrpclib import loads, dumps
except ImportError:
    from xmlrpc.client import loads, dumps
import warnings

from tg.support.registry import Registry, RegistryManager

from webtest import TestApp

import tg
from tg import tmpl_context, request_local, AppConfig
from tg.configuration import milestones

from tg.wsgiapp import TemplateContext, TGApp, RequestLocals
from tg.controllers import TGController

from .test_stack.baseutils import ControllerWrap, default_config

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')
cache_dir = os.path.join(data_dir, 'cache')

def setup_session_dir():
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

def teardown_session_dir():
    shutil.rmtree(session_dir, ignore_errors=True)

def make_app(controller_klass=None, environ=None, config_options=None, with_errors=False,
             make_app=True):
    """Creates a `TestApp` instance."""
    if controller_klass is None:
        controller_klass = TGController

    conf = AppConfig(root_controller=ControllerWrap(controller_klass),
                     **default_config)

    # Just let exceptions crash.
    conf['trace_errors.enable'] = False

    if with_errors:
        conf['errorpage.enabled'] = True
        conf['errorpage.status_codes'] = [403, 404]
    else:
        conf['errorpage.enabled'] = False

    conf['session.enabled'] = True
    conf['session.data_dir'] = session_dir
    conf['cache.enabled'] = True
    conf['cache.cache_dir'] = cache_dir

    if config_options is not None:
        for k, v in config_options.items():
            conf[k] = v

    if make_app:
        return TestApp(conf.make_wsgi_app())
    else:
        return conf


class TestWSGIController(TestCase):
    def setUp(self):
        tmpl_options = {}
        tmpl_options['genshi.search_path'] = ['tests']

        self._tgl = RequestLocals()
        self._tgl.tmpl_context = TemplateContext()
        request_local.context._push_object(self._tgl)

        # Mark configuration milestones as passed as
        # test sets up a fake configuration
        milestones._reach_all()

        warnings.simplefilter("ignore")
        tg.config.push_process_config(default_config)
        warnings.resetwarnings()
        setup_session_dir()

    def tearDown(self):
        request_local.context._pop_object(self._tgl)
        tg.config.pop_process_config()
        teardown_session_dir()

        # Reset milestones
        milestones._reset_all()

    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')

        return self.app.post(url, extra_environ=self.environ, params=kargs)

