# -*- coding: utf-8 -*-
"""
repoze.what & repoze.what-pylons **integration** tests.

Note that it is not necessary to have integration tests for the other auth*
software in this package. They must be in tg.devtools, specifically in the test
suite of the quickstarted applications (and there's where they are, as of
this writing).

"""

from unittest import TestCase
from shutil import rmtree
from urllib import unquote
import os

from paste import httpexceptions
from paste.registry import RegistryManager
from webob import Response, Request
from webtest import TestApp
from beaker.middleware import CacheMiddleware, SessionMiddleware

from tg import request, response, expose, require, allow_only
from tg.controllers import TGController, WSGIAppController, RestController
import pylons
from pylons import tmpl_context
from pylons.controllers.util import abort
from pylons.util import ContextObj, PylonsContext
from pylons.testutil import ControllerWrap, SetupCacheGlobal

from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
from repoze.what.middleware import setup_auth
from repoze.what.predicates import Not, is_user, not_anonymous

from pylons.middleware import StatusCodeRedirect
from tg.error import ErrorHandler

#{ AUT's setup
NOT_AUTHENTICATED = "The current user must have been authenticated"

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')

# Just in case...
rmtree(session_dir, ignore_errors=True)

def make_app(controller_klass, environ={}, with_errors=False):
    """Creates a ``TestApp`` instance."""
    # The basic middleware:
    app = ControllerWrap(controller_klass)
    app = SetupCacheGlobal(app, environ, setup_cache=True, setup_session=True)
    if with_errors:
        app = ErrorHandler(app, {}, debug=False)
        app = StatusCodeRedirect(app, [403, 404, 500])
    app = RegistryManager(app)
    app = SessionMiddleware(app, {}, data_dir=session_dir)
    app = CacheMiddleware(app, {}, data_dir=os.path.join(data_dir, 'cache'))

    # We're not going to use groups or permissions-related predicates here:
    groups_adapters = None
    permissions_adapters = None

    # Setting repoze.who up:
    cookie = AuthTktCookiePlugin('secret', 'authtkt')
    identifiers = [('cookie', cookie)]

    app = setup_auth(app, groups_adapters, permissions_adapters,
                     identifiers=identifiers, authenticators=[],
                     challengers=[], skip_authentication=True)

    app = httpexceptions.make_middleware(app)
    return TestApp(app)


#{ Mock objects


def wsgi_app(environ, start_response):
    """Mock WSGI application"""
    req = Request(environ)
    resp = Response("Hello from %s" % req.script_name + req.path_info)
    return resp(environ, start_response)


class DaRestController(RestController):
    """Mock REST controller"""

    allow_only = is_user('gustavo')

    @expose()
    def new(self):
        return "new here"


class HRManagementController(TGController):
    """Mock TG2 protected controller using the .allow_only attribute"""

    allow_only = is_user('hiring-manager')

    @expose()
    def index(self):
        return 'you can manage Human Resources'

    @expose()
    def hire(self, person_name):
        return "%s was just hired" % person_name


class ControlPanel(TGController):
    """Mock TG2 protected controller using @allow_only directly."""

    hr = HRManagementController()
    allow_only = not_anonymous()

    @expose()
    def index(self):
        return 'you are in the panel'

    @expose()
    @require(is_user('admin'))
    def add_user(self, user_name):
        return "%s was just registered" % user_name

class RootController(TGController):

    cp = ControlPanel()

    rest = DaRestController()

    mounted_app = WSGIAppController(wsgi_app, allow_only=is_user('gustavo'))

    @expose()
    def index(self):
        return "you're in the main page"

    @expose()
    @require(is_user('developer'))
    def commit(self):
        return 'you can commit'


class ControllerWithAllowOnlyAttributeAndAuthzDenialHandler(TGController):
    """Mock TG2 protected controller using the .allow_only attribute"""

    allow_only = is_user('foobar')

    @expose()
    def index(self):
        return 'Welcome back, foobar!'

    @classmethod
    def _failed_authorization(self, reason):
        # Pay first!
        abort(402)


class ControllerWithAllowOnlyDecoratorAndAuthzDenialHandler(TGController):
    """
    Mock TG2 protected controller using the @allow_only decorator, but also
    using ._failed_authorization()

    """

    @expose()
    def index(self):
        return 'Welcome back, foobar!'

    @classmethod
    def _failed_authorization(self, reason):
        # Pay first!
        abort(402)

ControllerWithAllowOnlyDecoratorAndAuthzDenialHandler = allow_only(
    is_user('foobar'))(ControllerWithAllowOnlyDecoratorAndAuthzDenialHandler)


#{ The tests themselves


class BaseIntegrationTests(TestCase):
    """Base test case for the integration tests"""

    controller = RootController

    def setUp(self):
        # Creating the session dir:
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
        # Setting TG2 up:
        c = ContextObj()
        py_obj = PylonsContext()
        py_obj.c = c
        py_obj.request = py_obj.response = None
        environ = {'pylons.routes_dict': dict(action='index'),
                   'pylons.pylons': py_obj}
        pylons.tmpl_context._push_object(c)
        # Finally, the app:
        self.app = make_app(self.controller, environ)

    def tearDown(self):
        tmpl_context._pop_object()
        # Removing the session dir:
        rmtree(session_dir, ignore_errors=True)

    def _check_flash(self, response, *expected_messages):
        """
        Check that ``expected_messages`` are defined in the WebFlash cookie.

        """
        assert 'webflash' in response.cookies_set, "Such no WebFlash cookie"
        flash = unquote(response.cookies_set['webflash'])
        for msg in expected_messages:
            msg = '"%s"' % msg
            assert msg in flash, 'Message %s not in flash: %s' % (msg, flash)


class TestRequire(BaseIntegrationTests):
    """Test case for the @require decorator"""

    def test_authz_granted_in_root_controller(self):
        environ = {'REMOTE_USER': 'developer'}
        resp = self.app.get('/commit', extra_environ=environ, status=200)
        self.assertEqual("you can commit", resp.body)

    def test_authz_denied_in_root_controller(self):
        # As an anonymous user:
        resp = self.app.get('/commit', status=401)
        assert "you can commit" not in resp.body
        self._check_flash(resp, r'The current user must be \"developer\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/commit', extra_environ=environ, status=403)
        assert "you can commit" not in resp.body
        self._check_flash(resp, r'The current user must be \"developer\"')

    def test_authz_granted_in_sub_controller(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body)

    def test_authz_denied_in_sub_controller(self):
        # As an anonymous user:
        resp = self.app.get('/cp/add_user/foo', status=401)
        assert "was just registered" not in resp.body
        self._check_flash(resp, NOT_AUTHENTICATED)
        # As an authenticated user:
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=403)
        assert "was just registered" not in resp.body
        self._check_flash(resp, r'The current user must be \"admin\"')


class TestAllowOnlyDecoratorInSubController(BaseIntegrationTests):
    """Test case for the @allow_only decorator in a sub-controller"""

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/cp/', extra_environ=environ, status=200)
        self.assertEqual("you are in the panel", resp.body)

    def test_authz_denied_without_require(self):
        resp = self.app.get('/cp/', status=401)
        assert "you are in the panel" not in resp.body
        self._check_flash(resp, NOT_AUTHENTICATED)

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body)

    def test_authz_denied_with_require(self):
        resp = self.app.get('/cp/add_user/foo', status=401)
        assert "was just registered" not in resp.body
        self._check_flash(resp, NOT_AUTHENTICATED)


class _TestAllowOnlyDecoratorAndDefaultAuthzDenialHandler(BaseIntegrationTests):
    """
    Test case for the @allow_only decorator in a controller using
    _failed_authorization() as its denial handler.

    """

    controller = ControllerWithAllowOnlyDecoratorAndAuthzDenialHandler

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("Welcome back, foobar!", resp.body)

    def test_authz_denied(self):
        resp = self.app.get('/', status=402)
        assert "Welcome back" not in resp.body


class TestAllowOnlyAttributeInSubController(BaseIntegrationTests):
    """Test case for the .allow_only attribute in a sub-controller"""

    controller = ControlPanel

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hr/', extra_environ=environ, status=200)
        self.assertEqual("you can manage Human Resources", resp.body)

    def test_authz_denied_without_require(self):
        # As an anonymous user:
        resp = self.app.get('/hr/', status=401)
        assert "you can manage Human Resources" not in resp.body
        self._check_flash(resp, r'The current user must have been authenticated')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hr/', extra_environ = environ, status=403)
        assert "you can manage Human Resources" not in resp.body
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hr/hire/gustavo', extra_environ=environ,
                            status=200)
        self.assertEqual("gustavo was just hired", resp.body)

    def test_authz_denied_with_require(self):
        # As an anonymous user:
        resp = self.app.get('/hr/hire/gustavo', status=401)
        assert "was just hired" not in resp.body
        self._check_flash(resp, r'The current user must have been authenticated')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hr/hire/gustavo', extra_environ = environ, status=403)
        assert "was just hired" not in resp.body
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')


class TestAllowOnlyAttributeAndDefaultAuthzDenialHandler(BaseIntegrationTests):
    """
    Test case for the .allow_only attribute in a controller using
    _failed_authorization() as its denial handler.

    """

    controller = ControllerWithAllowOnlyAttributeAndAuthzDenialHandler

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("Welcome back, foobar!", resp.body)

    def test_authz_denied(self):
        resp = self.app.get('/', status=402)
        assert "Welcome back" not in resp.body


class TestAppWideAuthzWithAllowOnlyDecorator(BaseIntegrationTests):
    """Test case for application-wide authz with the @allow_only decorator"""

    controller = ControlPanel

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("you are in the panel", resp.body)

    def test_authz_denied_without_require(self):
        resp = self.app.get('/', status=401)
        assert "you are in the panel" not in resp.body
        self._check_flash(resp, NOT_AUTHENTICATED)

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body)

    def test_authz_denied_with_require(self):
        resp = self.app.get('/add_user/foo', status=401)
        assert "was just registered" not in resp.body
        self._check_flash(resp, NOT_AUTHENTICATED)


class TestAppWideAuthzWithAllowOnlyAttribute(BaseIntegrationTests):
    """Test case for application-wide authz with the .allow_only attribute"""

    controller = HRManagementController

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("you can manage Human Resources", resp.body)

    def test_authz_denied_without_require(self):
        # As an anonymous user:
        resp = self.app.get('/', status=401)
        assert "you can manage Human Resources" not in resp.body
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/', extra_environ = environ, status=403)
        assert "you can manage Human Resources" not in resp.body
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hire/gustavo', extra_environ=environ,
                            status=200)
        self.assertEqual("gustavo was just hired", resp.body)

    def test_authz_denied_with_require(self):
        # As an anonymous user:
        resp = self.app.get('/hire/gustavo', status=401)
        assert "was just hired" not in resp.body
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hire/gustavo', extra_environ = environ, status=403)
        assert "was just hired" not in resp.body
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')


class TestProtectedRESTContoller(BaseIntegrationTests):
    """Test case for protected REST controllers"""

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'gustavo'}
        resp = self.app.get('/rest/new', extra_environ=environ,
                            status=200)
        self.assertEqual("new here", resp.body)

    def test_authz_denied(self):
        # As an anonymous user:
        resp = self.app.get('/rest/new', status=401)
        assert "new here" not in resp.body
        self._check_flash(resp, r'The current user must be \"gustavo\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'non-gustavo'}
        resp = self.app.get('/rest/new', extra_environ=environ, status=403)
        assert "new here" not in resp.body
        self._check_flash(resp, r'The current user must be \"gustavo\"')


class TestProtectedWSGIApplication(BaseIntegrationTests):
    """Test case for protected WSGI applications mounted on the controller"""

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'gustavo'}
        resp = self.app.get('/mounted_app/da-path', extra_environ=environ,
                            status=200)
        self.assertEqual("Hello from /mounted_app/da-path", resp.body)

    def test_authz_denied(self):
        # As an anonymous user:
        resp = self.app.get('/mounted_app/da-path', status=401)
        assert "Hello from /mounted_app/" not in resp.body
        self._check_flash(resp, r'The current user must be \"gustavo\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'non-gustavo'}
        resp = self.app.get('/mounted_app/da-path', extra_environ=environ,
                            status=403)
        assert "Hello from /mounted_app/" not in resp.body
        self._check_flash(resp, r'The current user must be \"gustavo\"')

class ErrorController(object):
    @expose()
    def document(self, *args, **kwargs):
        return request.environ.get('repoze.who.identity')['repoze.who.userid']

class DefaultLessTGController(TGController):
    error = ErrorController()

    @expose()
    def index(self):
        return request.environ.get('repoze.who.identity')['repoze.who.userid']

class TestLoggedErrorTGController(BaseIntegrationTests):
    def setUp(self):
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)
        # Setting TG2 up:
        c = ContextObj()
        py_obj = PylonsContext()
        py_obj.c = c
        py_obj.request = py_obj.response = None
        environ = {'pylons.routes_dict': dict(action='index'),
                   'pylons.pylons': py_obj}
        pylons.tmpl_context._push_object(c)
        self.app = make_app(DefaultLessTGController, environ, with_errors=True)

    def test_logged_index(self):
        resp = self.app.get('/index', extra_environ={'REMOTE_USER': 'gustavo'}, expect_errors=True)
        assert 'gustavo' in resp

    def test_logged_error(self):
        resp = self.app.get('/missing_page_for_sure', extra_environ={'REMOTE_USER': 'gustavo'}, expect_errors=True)
        assert 'gustavo' in resp 
        
#}
