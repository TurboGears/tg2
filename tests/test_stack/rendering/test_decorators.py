from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp
from pylons import tmpl_context
from tg.util import no_warn
from tg.configuration import config

def make_app():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'pylons.tmpl_context_attach_args': False

                                       }
                             )
    return app_from_config(base_config)

app = None
def setup():
    global app
    app = make_app()

class TestTGController(object):

    def setup(self):
        self.app = app

    def test_simple_jsonification(self):
        resp = self.app.get('/j/json')
        assert '{"a": "hello world", "b": true}' in resp.body

    def test_multi_dispatch_json(self):
        resp = self.app.get('/j/xml_or_json', headers={'accept':'application/json'})
        assert '''"status": "missing"''' in resp
        assert '''"name": "John Carter"''' in resp
        assert '''"title": "officer"''' in resp

    def test_json_with_object(self):
        resp = self.app.get('/j/json_with_object')
        assert '''"Json": "Rocks"''' in resp.body

    @no_warn
    def test_json_with_bad_object(self):
        try:
            resp = self.app.get('/j/json_with_bad_object')
        except TypeError, e:
            pass
        assert "is not JSON serializable" in str(e), str(e)

    def test_multiple_engines(self):
        default_renderer = config['default_renderer']
        resp = self.app.get('/multiple_engines')
        assert default_renderer in resp, resp

class TestExposeInheritance(object):
    def setup(self):
        self.app = app

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
