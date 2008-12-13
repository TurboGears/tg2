# -*- coding: utf-8 -*-

"""Stuff required to the authentication and authorization."""

import os, shutil
from unittest import TestCase
from xmlrpclib import loads, dumps

import webob
import beaker
import pylons
from paste.registry import Registry, RegistryManager
from paste.fixture import TestApp
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from paste import httpexceptions

from tg import tmpl_context
from pylons.util import ContextObj, PylonsContext
from pylons.controllers.util import Request, Response
from tg.controllers import TGController
from pylons.testutil import ControllerWrap, SetupCacheGlobal
#import pylons.tests

from beaker.middleware import CacheMiddleware

from repoze.who.plugins.form import RedirectingFormPlugin
from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.what.middleware import setup_auth
from repoze.what.adapters import BaseSourceAdapter
from pylons import config

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'fixture', 'session')

def setup_session_dir():
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

def teardown_session_dir():
    shutil.rmtree(session_dir, ignore_errors=True)

default_environ = {
    'pylons.use_webob' : True,
    'pylons.routes_dict': dict(action='index'),
    'paste.config': dict(global_conf=dict(debug=True))
}


class FakeAuthenticator(object):
    """Fake repoze.who authenticator plugin"""
    credentials = {
        u'rms': u'freedom',
        u'linus': u'linux',
        u'sballmer': u'developers',
        u'guido': u'pythonic',
        u'rasmus': u'php'
        }

    def authenticate(self, environ, identity):
        login = identity['login']
        pass_ = identity['password']
        if login in self.credentials and pass_ == self.credentials[login]:
            return login


class FakeGroupSourceAdapter(BaseSourceAdapter):
    """Mock group source adapter"""

    def __init__(self):
        super(FakeGroupSourceAdapter, self).__init__()
        self.fake_sections = {
            u'admins': set([u'rms']),
            u'developers': set([u'rms', u'linus']),
            u'trolls': set([u'sballmer']),
            u'python': set(),
            u'php': set()
            }

    def _get_all_sections(self):
        return self.fake_sections

    def _get_section_items(self, section):
        return self.fake_sections[section]

    def _find_sections(self, identity):
        username = identity['repoze.who.userid']
        return set([n for (n, g) in self.fake_sections.items()
                    if username in g])

    def _include_items(self, section, items):
        self.fake_sections[section] |= items

    def _exclude_items(self, section, items):
        for item in items:
            self.fake_sections[section].remove(item)

    def _item_is_included(self, section, item):
        return item in self.fake_sections[section]

    def _create_section(self, section):
        self.fake_sections[section] = set()

    def _edit_section(self, section, new_section):
        self.fake_sections[new_section] = self.fake_sections[section]
        del self.fake_sections[section]

    def _delete_section(self, section):
        del self.fake_sections[section]

    def _section_exists(self, section):
        return self.fake_sections.has_key(section)


class FakePermissionSourceAdapter(FakeGroupSourceAdapter):
    """Mock permissions source adapter"""

    def __init__(self):
        super(FakePermissionSourceAdapter, self).__init__()
        self.fake_sections = {
            u'see-site': set([u'trolls']),
            u'edit-site': set([u'admins', u'developers']),
            u'commit': set([u'developers'])
            }

    def _find_sections(self, group_name):
        return set([n for (n, p) in self.fake_sections.items()
                    if group_name in p])


def make_app(controller_klass=None, environ=None):
    """Creates a `TestApp` instance."""
    if environ is None:
        environ = {}
    environ['pylons.routes_dict'] = {}
    environ['pylons.routes_dict']['action'] = "routes_placeholder"

    if controller_klass is None:
        controller_klass = TGController

    app = ControllerWrap(controller_klass)
    app = SetupCacheGlobal(app, environ, setup_cache=True, setup_session=True)
    app = RegistryManager(app)
    app = beaker.middleware.SessionMiddleware(app, {}, data_dir=session_dir)
    app = CacheMiddleware(app, {}, data_dir=os.path.join(data_dir, 'cache'))

    # Setting up the source adapters:
    groups_adapters = {'my_groups': FakeGroupSourceAdapter()}
    permissions_adapters = {'my_permissions': FakePermissionSourceAdapter()}
    
    # Setting up repoze.who:
    cookie = AuthTktCookiePlugin('secret', 'authtkt')
    
    form = RedirectingFormPlugin('/login', '/login_handler',
                                 '/logout_handler',
                                 rememberer_name='cookie')
    
    identifiers = [('main_identifier', form), ('cookie', cookie)]
    challengers = [('form', form)]
    authenticators = (('auth', FakeAuthenticator()), )
    app = setup_auth(app, groups_adapters, permissions_adapters, 
                     identifiers=identifiers, authenticators=authenticators,
                     challengers=challengers)

    app = httpexceptions.make_middleware(app)
    return TestApp(app)


def create_request(path, environ=None):
    """Helper used in test cases to quickly setup a request obj.

    ``path``
        The path will become PATH_INFO
    ``environ``
        Additional environment

    Returns an instance of the `webob.Request` object.
    """
    # setup the environ
    if environ is None:
        environ = {}
    environ.update(default_environ)
    # create a "blank" WebOb Request object
    # using Pylon's Request which is a webob Request plus
    # some compatibility methods
    req = Request.blank(path, environ)
    # setup a Registry
    reg = environ.setdefault('paste.registry', Registry())
    reg.prepare()
    # setup pylons.request to point to our Registry
    reg.register(pylons.request, req)
    # setup tmpl context
    tmpl_context._push_object(ContextObj())
    return req

class TestWSGIController(TestCase):

    def setUp(self):
        tmpl_context._push_object(ContextObj())
        # Without the line below, it will fail because TG2 will try to use the
        # deprecated Buffet package.
        config['use_legacy_renderer'] = False

    def tearDown(self):
        tmpl_context._pop_object()

    def get_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.get(url, extra_environ=self.environ)

    def post_response(self, **kargs):
        url = kargs.pop('_url', '/')
        self.environ['pylons.routes_dict'].update(kargs)
        return self.app.post(url, extra_environ=self.environ, params=kargs)
