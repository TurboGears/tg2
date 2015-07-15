from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp

from nose import SkipTest
from tg._compat import PY3


def setup_noDB(prefer_tw2=False):

    base_config = TestConfig(folder = 'rendering',
                     values = {'use_sqlalchemy': False,
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': False,
                               'templating.genshi.method':'xhtml',
                               'prefer_toscawidgets2':prefer_tw2
                               }
                             )
    return app_from_config(base_config)


expected_fields = ['name="year"', 'name="title"']

def test_basic_form_rendering():
    if PY3: raise SkipTest()

    app = setup_noDB()
    resp = app.get('/form')
    assert "form" in resp

    for expected_field in expected_fields:
        assert expected_field in resp, resp

def test_tw2_form_rendering():
    app = setup_noDB(prefer_tw2=True)
    resp = app.get('/tw2form')
    assert "form" in resp

    for expected_field in expected_fields:
        assert expected_field in resp, resp
