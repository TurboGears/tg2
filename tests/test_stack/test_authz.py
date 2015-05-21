# -*- coding: utf-8 -*-
"""
repoze.who **integration** tests.

Note that it is not necessary to have integration tests for the other auth*
software in this package. They must be in tg.devtools, specifically in the test
suite of the quickstarted applications (and there's where they are, as of
this writing).

"""

from unittest import TestCase
from shutil import rmtree
import os
from nose.tools import raises

from tg._compat import url_unquote
from tg.configuration.utils import TGConfigError

from tg.support.registry import RegistryManager
from webob import Response, Request
from webtest import TestApp

from tg import request, response, expose, require, redirect
from tg.controllers import TGController, WSGIAppController, RestController
from tg.controllers.util import abort, auth_force_login, auth_force_logout
from tg.wsgiapp import TGApp
from tg.support.middlewares import CacheMiddleware, SessionMiddleware, StatusCodeRedirect
from tg.decorators import Decoration

from .baseutils import ControllerWrap, FakeRoutes, default_config
from ..base import make_app as base_make_app

from tg.configuration.auth import setup_auth, TGAuthMetadata
from tg.predicates import is_user, not_anonymous, in_group, has_permission

from tg.error import ErrorHandler

#{ AUT's setup
NOT_AUTHENTICATED = "The current user must have been authenticated"

data_dir = os.path.dirname(os.path.abspath(__file__))
session_dir = os.path.join(data_dir, 'session')

# Just in case...
rmtree(session_dir, ignore_errors=True)


class TestAuthMetadata(TGAuthMetadata):
    """
    Provides a way to lookup for user, groups and permissions
    given the current identity. This has to be specialized
    for each storage backend.

    By default it returns empty lists for groups and permissions
    and None for the user.
    """
    def get_user(self, identity, userid):
        if ':' in userid:
            return userid.split(':')[0]

        return super(TestAuthMetadata, self).get_user(identity, userid)

    def get_groups(self, identity, userid):
        if userid:
            parts = userid.split(':')
            return parts[1:2]

        return super(TestAuthMetadata, self).get_groups(identity, userid)

    def get_permissions(self, identity, userid):
        if userid:
            parts = userid.split(':')
            return parts[2:]

        return super(TestAuthMetadata, self).get_permissions(identity, userid)


def make_app(controller_klass, environ={}, with_errors=False, config_options=None):
    """Creates a ``TestApp`` instance."""
    authmetadata = TestAuthMetadata()

    config_options = config_options or {}
    config_options.setdefault('sa_auth', {})

    sa_auth = config_options['sa_auth']
    sa_auth.update({
        'authmetadata': authmetadata
    })

    app = base_make_app(controller_klass, environ, config_options, with_errors).app

    # Setting repoze.who up:
    from repoze.who.plugins.auth_tkt import AuthTktCookiePlugin
    cookie = AuthTktCookiePlugin('secret', 'authtkt')
    identifiers = [('cookie', cookie)]

    app = setup_auth(app, identifiers=identifiers, skip_authentication=True,
                     authenticators=[], challengers=[])

    # As setup_auth with skip_authentication sets empty authenticators always
    # we must manually append it after creating the middleware.
    app.api_factory.authenticators.append(('cookie', cookie))

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

class CustomAllowOnly(TGController):
    class something(object):
        def check_authorization(self, env):
            from tg.controllers.decoratedcontroller import NotAuthorizedError
            raise NotAuthorizedError()

    @expose()
    def index(self):
        return 'HI'

    allow_only = something()

class SmartDenialAllowOnly(TGController):
    allow_only = require(is_user('developer'), smart_denial=True)

    @expose('json')
    def data(self):
        return {'key': 'value'}

class RootController(TGController):
    custom_allow = CustomAllowOnly()
    smart_allow = SmartDenialAllowOnly()
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

    @expose('json:')
    @require(is_user('developer'), smart_denial=True)
    def smartabort(self):
        return {'key': 'value'}

    @expose()
    @require(in_group('managers'))
    @require(has_permission('commit'))
    def force_commit(self):
        return 'you can commit'

    @expose()
    def login_logout(self, username, noidentifier='0'):
        if noidentifier == '1':
            request.environ['repoze.who.plugins'] = {}

        if username == 'logout':
            auth_force_logout()
        else:
            auth_force_login('%s:managers' % username)

        return 'OK'

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


#{ The tests themselves


class BaseIntegrationTests(TestCase):
    """Base test case for the integration tests"""

    controller = RootController

    def setUp(self):
        # Creating the session dir:
        if not os.path.exists(session_dir):
            os.makedirs(session_dir)

        # Setting TG2 up:
        self.app = make_app(self.controller, {}, config_options=getattr(self, 'CONFIG_OPTIONS', {}))

    def tearDown(self):
        # Removing the session dir:
        rmtree(session_dir, ignore_errors=True)

    def _check_flash(self, response, *expected_messages):
        """
        Check that ``expected_messages`` are defined in the WebFlash cookie.

        """
        assert 'webflash' in response.cookies_set, "Such no WebFlash cookie"
        flash = url_unquote(response.cookies_set['webflash'])
        for msg in expected_messages:
            msg = '"%s"' % msg
            assert msg in flash, 'Message %s not in flash: %s' % (msg, flash)

class TestLoginLogout(BaseIntegrationTests):
    def test_user_login(self):
        resp = self.app.get('/login_logout?username=developer')
        cookie = resp.headers['Set-Cookie']
        assert 'authtkt="' in cookie
        assert 'developer' in cookie

    @raises(TGConfigError)
    def test_user_login_without_identifier(self):
        resp = self.app.get('/login_logout?username=developer&noidentifier=1')

    def test_user_logout(self):
        AUTH_TOKEN = 'authtkt="f0657f514a6b960d50ea199aea76534d53cd0dd4developer%3Amanagers!"'
        resp = self.app.get('/login_logout?username=logout', headers=[('Cookie', AUTH_TOKEN)])
        assert 'authtkt="INVALID"' in str(resp), resp

    def test_user_override(self):
        AUTH_TOKEN = 'authtkt="f0657f514a6b960d50ea199aea76534d53cd0dd4developer%3Amanagers!"'
        resp = self.app.get('/login_logout?username=admin', headers=[('Cookie', AUTH_TOKEN)])
        cookie = resp.headers['Set-Cookie']
        assert 'authtkt="' in cookie, resp
        assert 'admin' in cookie, resp

class TestRequire(BaseIntegrationTests):
    """Test case for the @require decorator"""

    def test_authz_custom_allow_only(self):
        #environ = {'REMOTE_USER': 'developer'}
        resp = self.app.get('/custom_allow', extra_environ={}, status=401)

    def test_authz_granted_in_root_controller(self):
        environ = {'REMOTE_USER': 'developer'}
        resp = self.app.get('/commit', extra_environ=environ, status=200)
        self.assertEqual("you can commit", resp.body.decode('utf-8'))

    def test_multiple_requirements_passed(self):
        environ = {'REMOTE_USER': 'developer:managers:commit'}
        resp = self.app.get('/force_commit', extra_environ=environ, status=200)
        self.assertEqual("you can commit", resp.text)

    def test_multiple_requirements_blocked_1(self):
        environ = {'REMOTE_USER': 'tester:testing:commit'}
        resp = self.app.get('/force_commit', extra_environ=environ, status=403)
        assert 'The current user must belong to the group "managers"' in resp.text, resp.text

    def test_multiple_requirements_blocked_2(self):
        environ = {'REMOTE_USER': 'manager:managers:viewonly'}
        resp = self.app.get('/force_commit', extra_environ=environ, status=403)
        assert 'The user must have the "commit" permission' in resp.text, resp.text

    def test_multiple_requirements_all_registered(self):
        deco = Decoration.get_decoration(RootController.force_commit)
        assert len(deco.requirements) == 2, deco.requirements

    def test_multiple_requirements_backward_compatibility(self):
        deco = Decoration.get_decoration(RootController.force_commit)
        predicate = deco.requirement.predicate
        assert isinstance(predicate, has_permission), predicate

    def test_no_requirements_backward_compatibility(self):
        deco = Decoration.get_decoration(RootController.force_commit)
        reqs = deco.requirements
        deco.requirements = []
        requirement = deco.requirement
        deco.requirements = reqs
        assert requirement is None, requirement

    def test_authz_denied_in_root_controller(self):
        # As an anonymous user:
        resp = self.app.get('/commit', status=401)
        assert "you can commit" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"developer\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/commit', extra_environ=environ, status=403)
        assert "you can commit" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"developer\"')

    def test_authz_granted_in_sub_controller(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body.decode('utf-8'))

    def test_authz_denied_in_sub_controller(self):
        # As an anonymous user:
        resp = self.app.get('/cp/add_user/foo', status=401)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)
        # As an authenticated user:
        environ = {'REMOTE_USER': 'foobar'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=403)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"admin\"')

    def test_smart_auth_json(self):
        nouser = {'accept': 'application/json'}
        baduser = {'accept': 'application/json',
                'REMOTE_USER': 'foobar'}
        gooduser = {'accept': 'application/json',
                'REMOTE_USER': 'developer'}

        resp = self.app.get('/smartabort.json', extra_environ=nouser, status=401)
        assert resp.status == '401 Unauthorized', 'Expected 401, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smartabort.json', extra_environ=baduser, status=403)
        assert resp.status == '403 Forbidden', 'Expected 403, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smartabort.json', extra_environ=gooduser, status=200)
        assert resp.status == '200 OK', 'Expected 200, got %s' % (resp.body)
        assert {'key': 'value'} == resp.json, resp.json

    def test_smart_auth_json_allow_only(self):
        nouser = {'accept': 'application/json'}
        baduser = {'accept': 'application/json',
                'REMOTE_USER': 'foobar'}
        gooduser = {'accept': 'application/json',
                'REMOTE_USER': 'developer'}

        resp = self.app.get('/smart_allow/data.json', extra_environ=nouser, status=401)
        assert resp.status == '401 Unauthorized', 'Expected 401, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smart_allow/data.json', extra_environ=baduser, status=403)
        assert resp.status == '403 Forbidden', 'Expected 403, got %s' % (resp.status)
        assert 'The current user must be "developer"' in resp.json['detail']

        resp = self.app.get('/smart_allow/data.json', extra_environ=gooduser, status=200)
        assert resp.status == '200 OK', 'Expected 200, got %s' % (resp.body)
        assert {'key': 'value'} == resp.json, resp.json


class TestAllowOnlyDecoratorInSubController(BaseIntegrationTests):
    """Test case for the @allow_only decorator in a sub-controller"""

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/cp/', extra_environ=environ, status=200)
        self.assertEqual("you are in the panel", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        resp = self.app.get('/cp/', status=401)
        assert "you are in the panel" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/cp/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        resp = self.app.get('/cp/add_user/foo', status=401)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)

class TestAllowOnlyAttributeInSubController(BaseIntegrationTests):
    """Test case for the .allow_only attribute in a sub-controller"""

    controller = ControlPanel

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hr/', extra_environ=environ, status=200)
        self.assertEqual("you can manage Human Resources", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        # As an anonymous user:
        resp = self.app.get('/hr/', status=401)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must have been authenticated')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hr/', extra_environ = environ, status=403)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hr/hire/gustavo', extra_environ=environ,
                            status=200)
        self.assertEqual("gustavo was just hired", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        # As an anonymous user:
        resp = self.app.get('/hr/hire/gustavo', status=401)
        assert "was just hired" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must have been authenticated')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hr/hire/gustavo', extra_environ = environ, status=403)
        assert "was just hired" not in resp.body.decode('utf-8')
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
        self.assertEqual("Welcome back, foobar!", resp.body.decode('utf-8'))

    def test_authz_denied(self):
        resp = self.app.get('/', status=402)
        assert "Welcome back" not in resp.body.decode('utf-8')

class TestAppWideAuthzWithAllowOnlyDecorator(BaseIntegrationTests):
    """Test case for application-wide authz with the @allow_only decorator"""

    controller = ControlPanel

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("you are in the panel", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        resp = self.app.get('/', status=401)
        assert "you are in the panel" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'admin'}
        resp = self.app.get('/add_user/foo', extra_environ=environ,
                            status=200)
        self.assertEqual("foo was just registered", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        resp = self.app.get('/add_user/foo', status=401)
        assert "was just registered" not in resp.body.decode('utf-8')
        self._check_flash(resp, NOT_AUTHENTICATED)


class TestAppWideAuthzWithAllowOnlyAttribute(BaseIntegrationTests):
    """Test case for application-wide authz with the .allow_only attribute"""

    controller = HRManagementController

    def test_authz_granted_without_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/', extra_environ=environ, status=200)
        self.assertEqual("you can manage Human Resources", resp.body.decode('utf-8'))

    def test_authz_denied_without_require(self):
        # As an anonymous user:
        resp = self.app.get('/', status=401)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/', extra_environ = environ, status=403)
        assert "you can manage Human Resources" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')

    def test_authz_granted_with_require(self):
        environ = {'REMOTE_USER': 'hiring-manager'}
        resp = self.app.get('/hire/gustavo', extra_environ=environ,
                            status=200)
        self.assertEqual("gustavo was just hired", resp.body.decode('utf-8'))

    def test_authz_denied_with_require(self):
        # As an anonymous user:
        resp = self.app.get('/hire/gustavo', status=401)
        assert "was just hired" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'someone'}
        resp = self.app.get('/hire/gustavo', extra_environ = environ, status=403)
        assert "was just hired" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"hiring-manager\"')


class TestProtectedRESTContoller(BaseIntegrationTests):
    """Test case for protected REST controllers"""

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'gustavo'}
        resp = self.app.get('/rest/new', extra_environ=environ,
                            status=200)
        self.assertEqual("new here", resp.body.decode('utf-8'))

    def test_authz_denied(self):
        # As an anonymous user:
        resp = self.app.get('/rest/new', status=401)
        assert "new here" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"gustavo\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'non-gustavo'}
        resp = self.app.get('/rest/new', extra_environ=environ, status=403)
        assert "new here" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"gustavo\"')


class TestProtectedWSGIApplication(BaseIntegrationTests):
    """Test case for protected WSGI applications mounted on the controller"""
    CONFIG_OPTIONS = {
        'make_body_seekable': True
    }

    def test_authz_granted(self):
        environ = {'REMOTE_USER': 'gustavo'}
        resp = self.app.get('/mounted_app/da-path', extra_environ=environ,
                            status=200)
        self.assertEqual("Hello from /mounted_app/da-path", resp.body.decode('utf-8'))

    def test_authz_denied(self):
        # As an anonymous user:
        resp = self.app.get('/mounted_app/da-path', status=401)
        assert "Hello from /mounted_app/" not in resp.body.decode('utf-8')
        self._check_flash(resp, r'The current user must be \"gustavo\"')
        # As an authenticated user:
        environ = {'REMOTE_USER': 'non-gustavo'}
        resp = self.app.get('/mounted_app/da-path', extra_environ=environ,
                            status=403)
        assert "Hello from /mounted_app/" not in resp.body.decode('utf-8')
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
        self.app = make_app(DefaultLessTGController, {}, with_errors=True)

    def test_logged_index(self):
        resp = self.app.get('/index', extra_environ={'REMOTE_USER': 'gustavo'}, expect_errors=True)
        assert 'gustavo' in resp

    def test_logged_error(self):
        resp = self.app.get('/missing_page_for_sure', extra_environ={'REMOTE_USER': 'gustavo'}, expect_errors=True)
        assert 'gustavo' in resp 


class TestDiscardingIdentityWhenUserNone(BaseIntegrationTests):
    CONFIG_OPTIONS = {
        'identity.allow_missing_user': False
    }

    def test_authz_custom_allow_only(self):
        resp = self.app.get('/custom_allow', extra_environ={}, status=401)

    def test_user_is_discarded_when_metadata_is_none(self):
        environ = {'REMOTE_USER': 'developer'}
        resp = self.app.get('/commit', extra_environ=environ, status=401)

    def test_user_is_kept_when_metadata_available(self):
        environ = {'REMOTE_USER': 'developer:managers:commit'}
        resp = self.app.get('/force_commit', extra_environ=environ, status=200)
        self.assertEqual("you can commit", resp.body.decode('utf-8'))

#}
