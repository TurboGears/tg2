from nose.tools import raises
from tests.test_stack import TestConfig, app_from_config
from tg.util import no_warn
from tg.configuration import config
from tg.configuration import milestones
from tg.decorators import Decoration, decode_params
import tg
import json

def make_app():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    return app_from_config(base_config)

class TestTGController(object):

    def setup(self):
        self.app = make_app()

    def test_simple_jsonification(self):
        resp = self.app.get('/j/json')
        expected = {"a": "hello world", "b": True}
        assert expected == resp.json_body

    def test_multi_dispatch_json(self):
        resp = self.app.get('/j/xml_or_json', headers={'accept':'application/json'})
        assert '''"status": "missing"''' in resp
        assert '''"name": "John Carter"''' in resp
        assert '''"title": "officer"''' in resp

    def test_json_with_object(self):
        resp = self.app.get('/j/json_with_object')
        assert '''"Json": "Rocks"''' in str(resp.body)

    @no_warn
    def test_json_with_bad_object(self):
        try:
            resp = self.app.get('/j/json_with_bad_object')
            assert False
        except Exception as e:
            assert "is not JSON serializable" in str(e), str(e)

    def test_multiple_engines(self):
        default_renderer = config['default_renderer']
        resp = self.app.get('/multiple_engines')
        assert default_renderer in resp, resp

    def test_decode_params_json(self):
        params = {'name': 'Name', 'surname': 'Surname'}
        resp = self.app.post_json('/echo_json', params)
        assert resp.json_body == params

    @raises(ValueError)
    def test_decode_params_notjson(self):
        @decode_params('xml')
        def _fakefunc():
            pass


class TestExposeInheritance(object):
    def setup(self):
        self.app = make_app()

    def test_inherited_expose_template(self):
        resp1 = self.app.get('/sub1/index')
        resp2 = self.app.get('/sub2/index')
        assert resp1.body == resp2.body

    def test_inherited_expose_override(self):
        resp1 = self.app.get('/sub1/index_override')
        resp2 = self.app.get('/sub2/index_override')
        assert resp1.body != resp2.body

    def test_inherited_expose_hooks(self):
        resp1 = self.app.get('/sub1/data')
        assert ('"v"' in resp1 and '"parent_value"' in resp1)
        resp2 = self.app.get('/sub2/data')
        assert ('"v"' in resp2 and '"parent_value"' in resp2 and '"child_value"' in resp2)


class TestExposeLazyInheritance(object):
    def test_lazy_inheritance(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose(inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubController.func)
        assert len(deco.engines) == 1, deco.engines
        assert deco.engines['text/html'][1] == 'template.html', deco.engines

    def test_lazy_inheritance_with_template(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose('new_template.html', inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubController.func)
        assert len(deco.engines) == 1, deco.engines
        assert deco.engines['text/html'][1] == 'new_template.html', deco.engines

    def test_lazy_inheritance_with_nested_template(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            @tg.expose('template.html', content_type='text/plain')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose('new_template.html', inherit=True)
            @tg.expose('new_template.html', content_type='text/plain')
            def func(self):
                pass

        class SubSubController(SubController):
            @tg.expose('new2_template.html', inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubSubController.func)
        assert len(deco.engines) == 2, deco.engines
        assert deco.engines['text/html'][1] == 'new2_template.html', deco.engines
        assert deco.engines['text/plain'][1] == 'new_template.html', deco.engines

    def test_lazy_inheritance_with_3nested_template(self):
        milestones.renderers_ready._reset()

        class BaseController(tg.TGController):
            @tg.expose('template.html')
            @tg.expose('template.html', content_type='text/plain')
            @tg.expose('template.html', content_type='text/javascript')
            def func(self):
                pass

        class SubController(BaseController):
            @tg.expose('new_template.html', inherit=True)
            @tg.expose('new_template.html', content_type='text/plain')
            @tg.expose('new_template.html', content_type='text/javascript')
            def func(self):
                pass

        class SubSubController(SubController):
            @tg.expose('new2_template.html', inherit=True)
            @tg.expose('new2_template.html', content_type='text/javascript')
            def func(self):
                pass

        class SubSubSubController(SubSubController):
            @tg.expose('new3_template.html', inherit=True)
            def func(self):
                pass

        milestones.renderers_ready.reach()

        deco = Decoration.get_decoration(SubSubSubController.func)
        assert len(deco.engines) == 3, deco.engines
        assert deco.engines['text/html'][1] == 'new3_template.html', deco.engines
        assert deco.engines['text/plain'][1] == 'new_template.html', deco.engines
        assert deco.engines['text/javascript'][1] == 'new2_template.html', deco.engines
