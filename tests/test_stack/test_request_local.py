from tg.request_local import Request, Response

class TestRequest(object):
    def test_language(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, da'})
        bmatch = r.languages_best_match()
        assert ['da', 'en-gb'] == bmatch

    def test_language_fallback(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, da'})
        bmatch = r.languages_best_match(fallback='it')
        assert ['da', 'en-gb', 'it'] == bmatch

    def test_language_fallback_already_there(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, it, da'})
        bmatch = r.languages_best_match(fallback='it')
        assert ['it'] == bmatch, bmatch

    def test_languages(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, it;q=0.9, da'})
        r.language = 'it'
        assert r.language == 'it'
        bmatch = r.languages
        assert ['da', 'it'] == bmatch, bmatch

    def test_match_accept(self):
        r = Request({}, headers={'Accept': 'text/html;q=0.5, foo/bar'})
        first_match = r.match_accept(['foo/bar'])
        assert first_match == 'foo/bar', first_match

    def test_signed_cookie(self):
        resp = Response()
        resp.signed_cookie('key_name', 'VALUE', secret='123')
        cookie = resp.headers['Set-Cookie']

        r = Request({}, headers={'Cookie':cookie})
        value = r.signed_cookie('key_name', '123')
        assert value == 'VALUE', value

        r = Request({}, headers={'Cookie':cookie})
        value = r.signed_cookie('non_existing', '123')
        assert not value

class TestResponse(object):
    def test_wsgi_response(self):
        r = Response()
        status, headers, body = r.wsgi_response()
        assert '200 OK' == status