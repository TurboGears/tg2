# -*- coding: utf-8 -*-

import sys
from nose import SkipTest
from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch, no_warn
from webtest import TestApp
from tg._compat import PY3, u_, im_func
from tg.configuration import milestones
from tg import expose
from tg.decorators import Decoration

try:
    from tgext.chameleon_genshi import ChameleonGenshiRenderer
except ImportError:
    ChameleonGenshiRenderer = None

def setup_noDB(extra_init=None):
    base_config = TestConfig(folder = 'rendering',
                     values = {'use_sqlalchemy': False,
                               # we want to test the new renderer functions
                               'use_legacy_renderer': False,
                               # in this test we want dotted names support
                               'use_dotted_templatenames': True,
                               'use_toscawidgets': False,
                               'use_toscawidgets2': False
                               }
                             )

    if extra_init is not None:
        extra_init(base_config)

    return app_from_config(base_config)

def test_default_chameleon_genshi_renderer():
    if ChameleonGenshiRenderer is None:
        raise SkipTest()

    def add_chameleon_renderer(app_config):
        app_config.register_rendering_engine(ChameleonGenshiRenderer)
        app_config.renderers.append('chameleon_genshi')

    app = setup_noDB(add_chameleon_renderer)

    # Manually add the exposition again as it was already discarded
    # due to chameleon_genshi not being in the available renderes.
    milestones.renderers_ready._reset()
    from .controllers.root import RootController
    controller = im_func(RootController.chameleon_index_dotted)
    expose('chameleon_genshi:tests.test_stack.rendering.templates.index')(controller)
    milestones.renderers_ready.reach()

    resp = app.get('/chameleon_index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_default_kajiki_renderer():
    app = setup_noDB()
    resp = app.get('/kajiki_index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_kajiki_i18n():
    app = setup_noDB()
    resp = app.get('/kajiki_i18n')
    assert u_("Your application is now running") in resp

def test_kajiki_i18n_de():
    app = setup_noDB()
    resp = app.get('/kajiki_i18n_de')
    assert u_("Ihre Anwendung läuft jetzt einwandfrei") in resp

def test_kajiki_missing_template():
    app = setup_noDB()

    try:
        resp = app.get('/kajiki_missing_template')
    except IOError as e:
        assert 'missing.xml not found' in str(e)
    else:
        assert False, 'Should have raised IOError'

def test_jinja_dotted():
    app = setup_noDB()
    resp = app.get('/jinja_dotted')
    assert "move along, nothing to see here" in resp, resp

def test_jinja_inherits_dotted():
    app = setup_noDB()
    resp = app.get('/jinja_inherits_dotted')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_inherits_mixed():
    # Mixed notation, dotted and regular
    app = setup_noDB()
    resp = app.get('/jinja_inherits_mixed')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_i18n():
    app = setup_noDB()
    resp = app.get('/jinja_i18n', status=200)

def test_jinja_i18n_en():
    app = setup_noDB()
    resp = app.get('/jinja_i18n_en')
    assert "Your application is now running" in resp

def test_jinja_i18n_de():
    app = setup_noDB()
    resp = app.get('/jinja_i18n_de')
    assert u_("Ihre Anwendung läuft jetzt einwandfrei") in resp

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/index_dotted')
    assert "Welcome" in resp, resp
    assert "TurboGears" in resp, resp

def test_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_dotted')
    assert "Inheritance template" in resp, resp
    assert "Master template" in resp, resp
 
def test_genshi_sub_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_dotted')
    assert "Inheritance template" in resp, resp
    assert "Master template" in resp, resp
    assert "from sub-template: sub.tobeincluded" in resp, resp

def test_genshi_sub_inheritance_frombottom():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_dotted_from_bottom')
    assert "Master template" in resp, resp
    assert "from sub-template: sub.frombottom_dotted" in resp, resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index_dotted')
    assert "<p>This is the mako index page</p>" in resp, resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits_dotted')
    assert "inherited mako page" in resp, resp
    assert "Inside parent template" in resp, resp
