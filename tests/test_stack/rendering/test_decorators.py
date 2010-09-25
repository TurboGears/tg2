from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp
from pylons import tmpl_context
from tg.util import no_warn

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
