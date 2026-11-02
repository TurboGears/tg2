
import pytest

from tg.caching import cached_property
from tg.request_local import Request, Response


class TestRequest(object):
    @pytest.mark.parametrize('path, encoding, expected', [
        ('/\xc3\xa4/a b%?', 'utf-8', '/%C3%A4/a%20b%25%3F'),
        ('/\xe4/a b%?', 'latin-1', '/%E4/a%20b%25%3F'),
        ('/\xc0/a b%?', 'utf-8', '/%C0/a%20b%25%3F'),
    ])
    def test_quoted_path_info(self, path, encoding, expected):
        r = Request({'PATH_INFO': path}, url_encoding=encoding)
        assert r.quoted_path_info == expected

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
        assert bmatch[-1] == 'it', bmatch

    def test_languages(self):
        r = Request({}, headers={'Accept-Language': 'en-gb;q=0.8, it;q=0.9, da'})
        r._language = "it"  # Fake there was a tg.i18n["lang"] option set.
        bmatch = r.languages
        assert bmatch[:2] == ['da', 'it'], bmatch
        assert bmatch[-1] == 'it'

    def test_match_accept(self):
        r = Request({}, headers={'Accept': 'text/html;q=0.5, foo/bar'})
        first_match = r.match_accept(['foo/bar'])
        assert first_match == 'foo/bar', first_match

    def test_state_is_cached_property(self):
        assert isinstance(Request.state, cached_property)

        r = Request({})
        assert r.state is r.state

    def test_state_maps_to_tg_environ_keys(self):
        environ = {'tg.original_response': 'ORIGINAL'}
        r = Request(environ)

        assert r.state['original_response'] == 'ORIGINAL'
        r.state['status_code_redirect'] = False

        assert environ['tg.status_code_redirect'] is False
        assert r.state.get('status_code_redirect') is False
        assert 'status_code_redirect' in r.state
        assert r.state.pop('status_code_redirect') is False
        assert 'tg.status_code_redirect' not in environ

    def test_disable_methods_use_request_state(self):
        r = Request({})

        r.disable_error_pages()
        r.disable_auth_challenger()

        assert r.state['status_code_redirect'] is False
        assert r.environ['tg.status_code_redirect'] is False
        assert r.environ['tg.wsgi.skip_auth_challenge'] is True
        assert 'tg.skip_auth_challenge' not in r.environ

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

    def test_content_type(self):
        r = Response()

        r.content_type = str('text/html')
        # Verify it's a native string, and not unicode.
        assert type(r.content_type) == str
        assert r.content_type == 'text/html'

        del r.content_type
        assert r.content_type is None
