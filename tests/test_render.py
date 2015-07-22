"""
Testing for TG2 Configuration
"""
from nose.tools import raises

import tg
from tg.render import MissingRendererError, _get_tg_vars
from tests.base import setup_session_dir, teardown_session_dir

from tg.configuration import AppConfig
from mako.exceptions import TemplateLookupException
from tg.util.webtest import test_context


def setup():
    setup_session_dir()
def teardown():
    teardown_session_dir()

class FakePackage:
    __name__ = 'tests'
    __file__ = __file__

    class lib:
        class app_globals:
            class Globals:
                pass

@raises(MissingRendererError)
def test_render_missing_renderer():
    conf = AppConfig(minimal=True)
    app = conf.make_wsgi_app()

    tg.render_template({}, 'gensh')

def test_jinja_lookup_nonexisting_template():
    conf = AppConfig(minimal=True)
    conf.use_dotted_templatenames = True
    conf.renderers.append('jinja')
    conf.package = FakePackage()
    app = conf.make_wsgi_app()

    from jinja2 import TemplateNotFound
    try:
        render_jinja = conf.render_functions['jinja']
        render_jinja('tg.this_template_does_not_exists',
                     {'app_globals':tg.config['tg.app_globals']})
        assert False
    except TemplateNotFound:
        pass

class TestMakoLookup(object):
    def setup(self):
        conf = AppConfig(minimal=True)
        conf.use_dotted_templatenames = True
        conf.renderers.append('mako')
        conf.package = FakePackage()
        self.conf = conf
        self.app = conf.make_wsgi_app()

    def test_adjust_uri(self):
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader

        assert mlookup.adjust_uri('this_template_should_pass_unaltered', None) == 'this_template_should_pass_unaltered'

        dotted_test = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        assert dotted_test.endswith('tests/test_stack/rendering/templates/mako_inherits_local.mak')

        dotted_test = mlookup.adjust_uri('local:test_stack.rendering.templates.mako_inherits_local', None)
        assert dotted_test.endswith('tests/test_stack/rendering/templates/mako_inherits_local.mak')

    def test_local_lookup(self):
        render_mako = self.conf.render_functions['mako']
        res = render_mako('tests.test_stack.rendering.templates.mako_inherits_local',
                          {'app_globals':tg.config['tg.app_globals']})
        assert 'inherited mako page' in res

    def test_passthrough_text_literal__check(self):
        from mako.template import Template
        t = Template('Hi')

        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader
        mlookup.template_cache['hi_template'] = t
        assert mlookup.get_template('hi_template') is t

    @raises(TemplateLookupException)
    def test__check_not_existing_anymore(self):
        from mako.template import Template
        t = Template('Hi', filename='deleted_template.mak')

        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader
        mlookup.template_cache['deleted_template'] = t
        mlookup.get_template('deleted_template')

    @raises(IOError)
    def test_never_existed(self):
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader

        mlookup.get_template('deleted_template')

    def test__check_should_reload_on_cache_expire(self):
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader

        template_path = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        t = mlookup.get_template(template_path) #cache the template
        t.output_encoding = 'FAKE_ENCODING'

        t = mlookup.get_template(template_path)
        assert t.output_encoding == 'FAKE_ENCODING'

        import os, stat
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
        render_mako = self.conf.render_functions['mako']
        mlookup = render_mako.loader
        mlookup.auto_reload = False

        template_path = mlookup.adjust_uri('tests.test_stack.rendering.templates.mako_inherits_local', None)
        t = mlookup.get_template(template_path) #cache the template
        t.output_encoding = 'FAKE_ENCODING'

        t = mlookup.get_template(template_path)
        assert t.output_encoding == 'FAKE_ENCODING'

        import os, stat
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