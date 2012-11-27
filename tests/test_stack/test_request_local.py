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