from webtest import TestApp
from nose.tools import raises
from webob import Request
from tg.support.statics import StaticsMiddleware, FileServeApp
from webob.exc import HTTPBadRequest, HTTPForbidden
from datetime import datetime

def FakeApp(environ, start_response):
    return ['APP']

class TestStatics(object):
    def setup(self):
        self.app = TestApp(StaticsMiddleware(FakeApp, './tests'))

    def test_plain_request(self):
        r = self.app.get('/test.html')
        assert 'Welcome to TurboGears 2.0' in r

    def test_unknown_content_type(self):
        r = self.app.get('/empty_file.unknown')
        assert r.content_type == 'application/octet-stream'
        assert 'EMPTY' in r

    def test_if_modified_since(self):
        r = self.app.get('/empty_file.unknown', headers={'If-Modified-Since':'Sat, 29 Oct 1994 19:43:31 GMT'})
        assert 'EMPTY' in r

    @raises(HTTPBadRequest)
    def test_if_modified_since_invalid_date(self):
        r = self.app.get('/empty_file.unknown', headers={'If-Modified-Since':'This is not a date'})

    def test_if_modified_since_future(self):
        next_year = datetime.utcnow()
        next_year.replace(year=next_year.year+1)

        r = self.app.get('/empty_file.unknown',
                         headers={'If-Modified-Since':FileServeApp.make_date(next_year)},
                         status=304)

    def test_if_none_match(self):
        r = self.app.get('/empty_file.unknown')
        etag = r.headers['ETag']

        r = self.app.get('/empty_file.unknown', headers={'If-None-Match':etag}, status=304)

    def test_if_none_match_different(self):
        r = self.app.get('/empty_file.unknown', headers={'If-None-Match':'Probably-Not-The-Etag'})
        assert 'EMPTY' in r

    def test_make_date(self):
        res = FileServeApp.make_date(datetime(2000, 1, 1, 0, 0, 0, 0))
        assert res == 'Sat, 01 Jan 2000 00:00:00 GMT'

    def test_304_on_post(self):
        r = self.app.post('/empty_file.unknown', status=304)

    def test_forbidden_path(self):
        r = self.app.get('/missing/../test.html', status=404)
        assert 'Out of bounds' in r

    def test_FileApp_non_existing_file(self):
        fa = TestApp(FileServeApp('this_does_not_exists.unknown', 0))
        r = fa.get('/', status=403)
        assert '403' in r

    def test_wsgi_file_wrapper(self):
        class DummyWrapper(object):
            def __init__(self, file, block_size):
                self.file = file
                self.block_size = block_size

        environ = {
            'wsgi.url_scheme': 'http',
            'wsgi.version':(1,0),
            'wsgi.file_wrapper': DummyWrapper,
            'SERVER_NAME': 'somedomain.com',
            'SERVER_PORT': '8080',
            'PATH_INFO': '/index.html',
            'SCRIPT_NAME': '',
            'REQUEST_METHOD': 'GET',
            }

        app = FileServeApp('./tests/test.html', 3600)
        app_iter = Request(environ).send(app).app_iter
        assert isinstance(app_iter, DummyWrapper)
        assert b'Welcome to TurboGears 2.0' in app_iter.file.read()
        app_iter.file.close()
