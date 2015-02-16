from webtest import TestApp
from tg.support.middlewares import StatusCodeRedirect
from tg.support.middlewares import DBSessionRemoverMiddleware
from tg.support.middlewares import MingSessionRemoverMiddleware


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


class FakeDBSession(object):
    removed = False

    def remove(self):
        self.removed = True

    def close_all(self):
        self.remove()


class FakeAppWithClose(object):
    closed = False
    step = 0

    def __call__(self, environ, start_response):
        start_response('200 Success', [])

        if environ['PATH_INFO'] == '/crash':
            raise Exception('crashed')

        return self

    def __iter__(self):
        return self

    def next(self):
        self.step += 1

        if self.step > 3:
            raise StopIteration()

        return str(self.step)

    def close(self):
        self.closed = True

    def __repr__(self):
        return '%s - %s' % (self.step, self.closed)


class TestDBSessionRemoverMiddleware(object):
    def setup(self):
        self.app_with_close = FakeAppWithClose()
        self.session = FakeDBSession()
        self.app = TestApp(DBSessionRemoverMiddleware(self.session, self.app_with_close))

    def test_close_is_called(self):
        r = self.app.get('/nonerror')
        assert self.app_with_close.closed == True, self.app_with_close

    def test_session_is_removed(self):
        r = self.app.get('/nonerror')
        assert self.session.removed == True, self.app_with_close

    def test_session_is_removed_on_crash(self):
        try:
            r = self.app.get('/crash')
        except:
            pass

        assert self.session.removed == True, self.app_with_close


class TestMingSessionRemoverMiddlewaree(object):
    def setup(self):
        self.app_with_close = FakeAppWithClose()
        self.session = FakeDBSession()
        self.app = TestApp(MingSessionRemoverMiddleware(self.session, self.app_with_close))

    def test_close_is_called(self):
        r = self.app.get('/nonerror')
        assert self.app_with_close.closed == True, self.app_with_close

    def test_session_is_removed(self):
        r = self.app.get('/nonerror')
        assert self.session.removed == True, self.app_with_close

    def test_session_is_removed_on_crash(self):
        try:
            r = self.app.get('/crash')
        except:
            pass

        assert self.session.removed == True, self.app_with_close
