# -*- coding: utf-8 -*-
from nose.tools import raises
from webtest import TestApp
import gettext as _gettext

import tg
from tg import i18n, expose, TGController, config
from tg.configuration import AppConfig

from tg._compat import unicode_text, u_

class _FakePackage:
    __name__ = 'tests'
    __file__ = __file__

    class lib:
        class app_globals:
            class Globals:
                pass
_FakePackage.__name__ = 'tests'

class TestSanitizeLanguage():
    def test_sanitize_language_code(self):
        """Check that slightly malformed language codes can be corrected."""
        for lang in 'pt', 'PT':
            assert i18n.sanitize_language_code(lang) == 'pt'
        for lang in 'pt-br', 'pt_br', 'pt_BR':
            assert i18n.sanitize_language_code(lang) == 'pt_BR'
        for lang in 'foo', 'bar', 'foo-bar':
            assert i18n.sanitize_language_code(lang) == lang

    def test_sanitize_language_code_charset(self):
        assert i18n.sanitize_language_code('en_US.UTF-8') == 'en_US'

    def test_sanitize_language_code_modifier(self):
        assert i18n.sanitize_language_code('it_IT@euro') == 'it_IT'

    def test_sanitize_language_code_charset_and_modifier(self):
        assert i18n.sanitize_language_code('de_DE.iso885915@euro') == 'de_DE'

    def test_sanitize_language_code_territory_script_variant(self):
        assert i18n.sanitize_language_code('zh_Hans_CN') == 'zh_CN'

    def test_sanitize_language_code_numeric(self):
        assert i18n.sanitize_language_code('es-419') == 'es_419'

    def test_sanitize_language_code_numeric_variant(self):
        assert i18n.sanitize_language_code('de-CH-1996') == 'de_CH'

def test_formencode_gettext_nulltranslation():
    prev_gettext = i18n.ugettext
    def nop_gettext(v):
        return v

    i18n.ugettext = nop_gettext
    assert i18n._formencode_gettext('something') == 'something'
    i18n.ugettext = prev_gettext
    return 'OK'

@raises(i18n.LanguageError)
def test_get_unaccessible_translator():
    def _fake_find(*args, **kwargs):
        return '/fake_file'

    real_find = _gettext.find
    _gettext.find = _fake_find
    try:
        i18n._get_translator(['de'], tg_config={'localedir': '',
                                                'package': _FakePackage()})
    finally:
        _gettext.find = real_find

class i18nRootController(TGController):
    def _before(self, *args, **kw):
        if not tg.request.GET.get('skip_lang'):
            forced_lang = tg.request.GET.get('force_lang', 'de')
            forced_lang = forced_lang.split(',')
            i18n.set_temporary_lang(forced_lang)

        if tg.request.GET.get('fallback'):
            i18n.add_fallback(tg.request.GET.get('fallback'),
                              fallback=tg.request.GET.get('fallback-fallback', False))

    @expose('json')
    def lazy_hello(self, **kw):
        return dict(text=unicode_text(i18n.lazy_ugettext('Your application is now running')))

    @expose('json')
    def get_lang(self, **kw):
        return dict(lang=i18n.get_lang())

    @expose('json')
    def get_supported_lang(self, **kw):
        return dict(lang=i18n.get_lang(all=False))

    @expose('json')
    def hello(self, **kw):
        return dict(text=unicode_text(i18n.ugettext('Your application is now running')))

    @expose()
    def fallback(self, **kw):
        return i18n.ugettext('This is a fallback')

    @expose('json')
    def hello_plural(self):
        return dict(text=i18n.ungettext('Your application is now running',
                                        'Your applications are now running',
                                        2))

    @expose()
    def force_german(self, **kw):
        i18n.set_lang('de')
        return 'OK'


class TestI18NStack(object):
    def setup(self):
        conf = AppConfig(minimal=True, root_controller=i18nRootController())
        conf['paths']['root'] = 'tests'
        conf['i18n.enabled'] = True
        conf['session.enabled'] = True
        conf['i18n.lang'] = None
        conf['beaker.session.key'] = 'tg_test_session'
        conf['beaker.session.secret'] = 'this-is-some-secret'
        conf.renderers = ['json']
        conf.default_renderer = 'json'
        conf.package = _FakePackage()
        app = conf.make_wsgi_app()
        self.app = TestApp(app)

    def teardown(self):
        config.pop('tg.root_controller')

    def test_lazy_gettext(self):
        r = self.app.get('/lazy_hello')
        assert 'Ihre Anwendung' in r

    def test_plural_gettext(self):
        r = self.app.get('/hello_plural')
        assert 'Your applications' in r, r

    def test_get_lang(self):
        r = self.app.get('/get_lang?skip_lang=1')
        assert '[]' in r, r.body

    def test_gettext_default_lang(self):
        r = self.app.get('/hello?skip_lang=1')
        assert 'Your application' in r, r

    def test_gettext_nop(self):
        k = 'HELLO'
        assert i18n.gettext_noop(k) is k

    def test_null_translator(self):
        assert i18n._get_translator(None).gettext('Hello') == 'Hello'

    def test_get_lang_nonexisting_lang(self):
        r = self.app.get('/get_lang?force_lang=fa')
        assert 'fa' in r, r

    def test_get_lang_existing(self):
        r = self.app.get('/get_lang?force_lang=de')
        assert 'de' in r, r

    def test_fallback(self):
        r = self.app.get('/fallback?force_lang=it&fallback=de')
        assert 'Dies ist' in r, r

    @raises(i18n.LanguageError)
    def test_fallback_non_existing(self):
        r = self.app.get('/fallback?force_lang=it&fallback=ko')

    def test_fallback_fallback(self):
        r = self.app.get('/fallback?force_lang=it&fallback=ko&fallback-fallback=true')
        assert 'This is a fallback' in r, r

    def test_get_lang_supported(self):
        r = self.app.get('/get_supported_lang?force_lang=it,ru,fa,de')
        langs = r.json['lang']
        assert langs == ['ru', 'de'], langs

    def test_get_lang_supported_without_lang(self):
        r = self.app.get('/get_supported_lang?skip_lang=1')
        langs = r.json['lang']
        assert langs == [], langs

    def test_force_lang(self):
        r = self.app.get('/get_lang?skip_lang=1')
        assert '[]' in r, r.body

        r = self.app.get('/force_german?skip_lang=1')
        assert 'tg_test_session' in r.headers.get('Set-cookie')

        cookie_value = r.headers.get('Set-cookie')
        r = self.app.get('/get_lang?skip_lang=1', headers={'Cookie':cookie_value})
        assert 'de' in r

    def test_get_lang_no_session(self):
        r = self.app.get('/get_lang?skip_lang=1', extra_environ={})
        assert '[]' in r, r.body


class TestI18NStackDefaultLang(object):
    def setup(self):
        conf = AppConfig(minimal=True, root_controller=i18nRootController())
        conf['paths']['root'] = 'tests'
        conf['i18n.enabled'] = True
        conf['session.enabled'] = True
        conf['i18n.lang'] = 'kr'
        conf['beaker.session.key'] = 'tg_test_session'
        conf['beaker.session.secret'] = 'this-is-some-secret'
        conf.renderers = ['json']
        conf.default_renderer = 'json'
        conf.package = _FakePackage()
        app = conf.make_wsgi_app()
        self.app = TestApp(app)

    def test_get_lang_supported_with_default_lang(self):
        r = self.app.get('/get_supported_lang?skip_lang=1',
                         headers={'Accept-Language': 'ru,en,de;q=0.5'})
        langs = r.json['lang']
        assert langs == ['ru', 'de', 'kr'], langs


class TestI18NStackDeprecatedDefaultLang(object):
    def setup(self):
        conf = AppConfig(minimal=True, root_controller=i18nRootController())
        conf['paths']['root'] = 'tests'
        conf['i18n.enabled'] = True
        conf['session.enabled'] = True
        conf['lang'] = 'kr'
        conf['beaker.session.key'] = 'tg_test_session'
        conf['beaker.session.secret'] = 'this-is-some-secret'
        conf.renderers = ['json']
        conf.default_renderer = 'json'
        conf.package = _FakePackage()
        app = conf.make_wsgi_app()
        self.app = TestApp(app)

    def test_get_lang_supported_with_default_lang(self):
        r = self.app.get('/get_supported_lang?skip_lang=1',
                         headers={'Accept-Language': 'ru,en,de;q=0.5'})
        langs = r.json['lang']
        assert langs == ['ru', 'de', 'kr'], langs
