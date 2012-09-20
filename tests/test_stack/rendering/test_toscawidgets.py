from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp

from nose import SkipTest
from tg._compat import PY3


def setup_noDB():

    base_config = TestConfig(folder = 'rendering',
                     values = {'use_sqlalchemy': False,
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': False,
                               'templating.genshi.method':'xhtml'
                               }
                             )
    return app_from_config(base_config)


expected_field = """\
<td class="fieldcol">
                <input type="text" name="year" class="textfield" id="movie_form_year" value="1984" size="4" />
            </td>"""

def test_basic_form_rendering():
    if PY3: raise SkipTest()

    app = setup_noDB()
    resp = app.get('/form')
    assert "form" in resp
    assert expected_field in resp, resp


