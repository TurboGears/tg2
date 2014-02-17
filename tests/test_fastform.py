from webob.exc import HTTPFound, HTTPUnauthorized
from tg.configuration.auth.fastform import FastFormPlugin

class FakeCookieAuth(object):
    def remember(self, *args, **kw):
        return 'REMEMBER'

    def forget(self, *args, **kw):
        return 'FORGET'

def build_env(path_info, qs='', SCRIPT_NAME=''):
    environ = {
        'PATH_INFO': path_info,
        'SCRIPT_NAME': SCRIPT_NAME,
        'QUERY_STRING': qs,
        'SERVER_NAME': 'example.org',
        'SERVER_PORT': '80',
        'wsgi.input': '',
        'wsgi.url_scheme': 'http',
        'CONTENT_TYPE': "application/x-www-form-urlencoded",
        }

    environ['repoze.who.plugins'] = {'cookie': FakeCookieAuth()}

    return environ


class TestFastFormPlugin(object):
    def setup(self):
        self.fform = FastFormPlugin('/login', '/login_handler', '/post_login', '/logout_handler',
                                    '/post_logout', 'cookie')

    def test_login(self):
        env = build_env('/login_handler', 'login=user&password=pwd&came_from=/goback')
        cred = self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPFound)
        assert cred['login'] == 'user'
        assert cred['password'] == 'pwd'
        assert env['repoze.who.application'].location == '/post_login?came_from=%2Fgoback'

    def test_login_nocred(self):
        env = build_env('/login_handler', 'login=user&came_from=/goback')
        cred = self.fform.identify(env)
        assert cred is None

    def test_login_counter(self):
        env = build_env('/login_handler', 'login=user&password=pwd&__logins=1')
        cred = self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPFound)
        assert cred['login'] == 'user'
        assert cred['password'] == 'pwd'
        assert env['repoze.who.application'].location == '/post_login?__logins=1'

    def test_login_counter_keep(self):
        env = build_env('/login', '__logins=1')
        self.fform.identify(env)

        assert 'logins' not in env['QUERY_STRING']
        assert env['repoze.who.logins'] == 1

    def test_logout_handler(self):
        env = build_env('/logout_handler', 'came_from=%2Fgoback')
        self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPUnauthorized)
        assert env['came_from'] == '/goback'

    def test_logout_handler_no_came_from(self):
        env = build_env('/logout_handler')
        self.fform.identify(env)

        assert isinstance(env['repoze.who.application'], HTTPUnauthorized)
        assert env['came_from'] == '/'

    def test_logout_handler_challenge(self):
        env = build_env('/logout_handler', 'came_from=%2Fgoback')
        self.fform.identify(env)
        ans = self.fform.challenge(env, '401 Unauthorized', [('app', '1')], [('forget', '1')])

        assert isinstance(ans, HTTPFound)
        assert ans.location == '/post_logout?came_from=%2Fgoback'

    def test_challenge_redirect_to_form(self):
        env = build_env('/private', SCRIPT_NAME='/SOMEWHERE')
        ans = self.fform.challenge(env, '401 Unauthorized', [('app', '1')], [('forget', '1')])

        assert isinstance(ans, HTTPFound)
        assert ans.location == '/SOMEWHERE/login?came_from=%2FSOMEWHERE%2Fprivate'

    def test_challenge_redirect_to_form_with_args(self):
        env = build_env('/private', qs='A=1&B=2', SCRIPT_NAME='/SOMEWHERE')
        ans = self.fform.challenge(env, '401 Unauthorized', [('app', '1')], [('forget', '1')])

        assert isinstance(ans, HTTPFound)

        # Cope with different dictionary ordering on Py2 and Py3
        assert ans.location in ('/SOMEWHERE/login?came_from=%2FSOMEWHERE%2Fprivate%3FA%3D1%26B%3D2',
                                '/SOMEWHERE/login?came_from=%2FSOMEWHERE%2Fprivate%3FB%3D2%26A%3D1'), ans.location

    def test_remember_forget(self):
        env = build_env('/private', SCRIPT_NAME='/SOMEWHERE')
        assert self.fform.remember(env, {}) == 'REMEMBER'
        assert self.fform.forget(env, {}) == 'FORGET'

    def test_repr(self):
        assert repr(self.fform).startswith('<FastFormPlugin:/login_handler')
