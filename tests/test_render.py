"""
Testing for TG2 Configuration
"""
import pytest
from mako.exceptions import TemplateLookupException
from webtest import TestApp

import tg
from tests.base import setup_session_dir, teardown_session_dir
from tg import AppConfig
from tg.render import MissingRendererError, _get_tg_vars
from tg.util.webtest import test_context


def setup_module():
    setup_session_dir()
def teardown_module():
    teardown_session_dir()

class FakePackage:
    __name__ = 'tests'
    __file__ = __file__

    class lib:
        class app_globals:
            class Globals:
                pass

def test_render_missing_renderer():
    conf = AppConfig(minimal=True)
    app = conf.make_wsgi_app()

    with pytest.raises(MissingRendererError):
        tg.render_template({}, 'gensh')


def test_render_default():
    conf = AppConfig(minimal=True)
    conf.default_renderer = 'json'
    app = conf.make_wsgi_app()

    res = tg.render_template({'value': 'value'})
    assert 'value": "value' in res


def test_jinja_lookup_nonexisting_template():
    conf = AppConfig(minimal=True)
    conf.use_dotted_templatenames = True
    conf.renderers.append('jinja')
    conf.package = FakePackage()
    app = conf.make_wsgi_app()

    from jinja2 import TemplateNotFound
    try:
        render_jinja = tg.config['render_functions']['jinja']
        render_jinja('tg.this_template_does_not_exists',
                     {'app_globals':tg.config['tg.app_globals']})
        assert False
    except TemplateNotFound:
        pass


class TestKajikiSupport(object):
    def setup_method(self):
        conf = AppConfig(minimal=True)
        conf.use_dotted_templatenames = True
        conf.renderers.append('kajiki')
        conf.package = FakePackage()
        self.conf = conf
        self.app = TestApp(conf.make_wsgi_app())
        self.render = tg.config['render_functions']['kajiki']

    def test_template_found(self):
        with test_context(self.app):
            res = self.render('tests.test_stack.rendering.templates.kajiki_i18n', {})
        assert 'Your application is now running' in res

    def test_dotted_template_not_found(self):
        try:
            with test_context(self.app):
                res = self.render('tests.test_stack.rendering.templates.this_doesnt_exists', {})
        except IOError as e:
            assert 'this_doesnt_exists.xhtml not found' in str(e)
        else:
            raise AssertionError('Should have raised IOError')

    def test_filename_template_not_found(self):
        try:
            with test_context(self.app):
                res = self.render('this_doesnt_exists/this_doesnt_exists.xhtml', {})
        except IOError as e:
            assert 'this_doesnt_exists.xhtml not found in template paths' in str(e)
        else:
            raise AssertionError('Should have raised IOError')


class TestMakoLookup(object):
    def setup_method(self):
        conf = AppConfig(minimal=True)
        conf.use_dotted_templatenames = True
        conf.renderers.append('mako')
        conf.package = FakePackage()
        self.conf = conf
        self.app = conf.make_wsgi_app()

    def test_adjust_uri(self):
        render_mako = tg.config['render_functions']['mako']
        mlookup = render_mako.dotted_loader

        assert mlookup.adjust_uri('this_template_should_pass_unaltered', None) == 'this_template_should_pass_unaltered'

        dotted_test = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        assert dotted_test.replace('\\', '/').endswith('tests/test_stack/rendering/templates/mako_inherits_local.mak')

        dotted_test = mlookup.adjust_uri('local:test_stack.rendering.templates.mako_inherits_local', None)
        assert dotted_test.replace('\\', '/').endswith('tests/test_stack/rendering/templates/mako_inherits_local.mak')

    def test_local_lookup(self):
        render_mako = tg.config['render_functions']['mako']
        res = render_mako('tests.test_stack.rendering.templates.mako_inherits_local',
                          {'app_globals':tg.config['tg.app_globals']})
        assert 'inherited mako page' in res

    def test_passthrough_text_literal__check(self):
        from mako.template import Template
        t = Template('Hi')

        render_mako = tg.config['render_functions']['mako']
        mlookup = render_mako.dotted_loader
        mlookup.template_cache['hi_template'] = t
        assert mlookup.get_template('hi_template') is t

    def test__check_not_existing_anymore(self):
        from mako.template import Template
        t = Template('Hi', filename='deleted_template.mak')

        render_mako = tg.config['render_functions']['mako']
        mlookup = render_mako.dotted_loader
        mlookup.template_cache['deleted_template'] = t

        with pytest.raises(TemplateLookupException):
            mlookup.get_template('deleted_template')

    def test_never_existed(self):
        render_mako = tg.config['render_functions']['mako']
        mlookup = render_mako.dotted_loader

        with pytest.raises(IOError):
            mlookup.get_template('deleted_template')

    def test__check_should_reload_on_cache_expire(self):
        render_mako = tg.config['render_functions']['mako']
        mlookup = render_mako.dotted_loader

        template_path = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        t = mlookup.get_template(template_path) #cache the template
        t.output_encoding = 'FAKE_ENCODING'

        t = mlookup.get_template(template_path)
        assert t.output_encoding == 'FAKE_ENCODING'

        import os
        import stat
        def fake_os_stat(o):
            return {stat.ST_MTIME:t.module._modified_time+1}

        old_stat = os.stat
        os.stat = fake_os_stat
        try:
            t = mlookup.get_template(template_path)
            #if the template got reloaded should not have our fake encoding anymore
            assert t.output_encoding != 'FAKE_ENCODING'
        finally:
            os.stat = old_stat

    def test__check_should_not_reload_when_disabled(self):
        render_mako = tg.config['render_functions']['mako']
        mlookup = render_mako.dotted_loader
        mlookup.auto_reload = False

        template_path = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        t = mlookup.get_template(template_path) #cache the template
        t.output_encoding = 'FAKE_ENCODING'

        t = mlookup.get_template(template_path)
        assert t.output_encoding == 'FAKE_ENCODING'

        import os
        import stat
        def fake_os_stat(o):
            return {stat.ST_MTIME:t.module._modified_time+1}

        old_stat = os.stat
        os.stat = fake_os_stat
        try:
            t = mlookup.get_template(template_path)
            assert t.output_encoding == 'FAKE_ENCODING'
        finally:
            os.stat = old_stat

    def test_fallback_validation_context_in_templates(self):
        with test_context(None, '/'):
            vars = _get_tg_vars()
            assert vars.tg.errors == {}, vars.tg
            assert vars.tg.inputs == {}, vars.tg
