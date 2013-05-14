from webtest import TestApp
from tg.support.middlewares import StatusCodeRedirect


def FakeApp(environ, start_response):
    if environ['PATH_INFO'].startswith('/error'):
        start_response('403 Forbidden', [])
    else:
        start_response('200 Success', [])

    if environ['PATH_INFO'] == '/error/document':
        yield b'ERROR!!!'
    else:
        yield b'HI'
        yield b'MORE'


class TestStatusCodeRedirectMiddleware(object):
    def setup(self):
        self.app = TestApp(StatusCodeRedirect(FakeApp, [403]))

    def test_error_redirection(self):
        r = self.app.get('/error_test', status=403)
        assert 'ERROR!!!' in r, r

    def test_success_passthrough(self):
        r = self.app.get('/success_test')
        assert 'HI' in r, r
