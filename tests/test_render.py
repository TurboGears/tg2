"""
Testing for TG2 Configuration
"""
from nose.tools import raises
from nose import SkipTest

import tg
from tg.render import MissingRendererError, render_jinja
from tests.base import TestWSGIController, make_app, setup_session_dir, teardown_session_dir, create_request

from tg.configuration import AppConfig
from tg._compat import PY3

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
    conf.renderers.append('jinja')
    conf.package = FakePackage
    app = conf.make_wsgi_app()

    from jinja2 import TemplateNotFound
    try:
        render_jinja('tg.this_template_does_not_exists', {'app_globals':tg.config['tg.app_globals']})
        assert False
    except TemplateNotFound:
        pass

