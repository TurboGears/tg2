from tg.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp
from pylons import tmpl_context

def setup_noDB():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       }
                             )
    return app_from_config(base_config)

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/')
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits')
    assert "Inheritance template" in resp
    assert "Master template" in resp

def test_genshi_sub_inheritance():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub')
    assert "Inheritance template" in resp
    assert "Master template" in resp
    assert "from sub-template: sub.tobeincluded" in resp

def test_genshi_sub_inheritance_from_bottom():
    app = setup_noDB()
    resp = app.get('/genshi_inherits_sub_from_bottom')
    assert "from sub-template: sub.frombottom" in resp
    assert "Master template" in resp

def test_chameleon_genshi_base():
    app = setup_noDB()
    resp = app.get('/chameleon_genshi_index')
    assert "<p>TurboGears 2 is rapid web application development toolkit designed to make your life easier.</p>" in resp

def test_chameleon_genshi_inheritance():
    app = setup_noDB()
    resp = app.get('/chameleon_genshi_inherits')
    assert "Inheritance template" in resp
    assert "Master template" in resp

def _test_jinja_inherits():
    app = setup_noDB()
    resp = app.get('/jinja_inherits')
    print resp
    assert "Welcome on my awsome homepage" in resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index')
    print resp
    assert "<p>This is the mako index page</p>" in resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits')
    print resp
    assert "inherited mako page" in resp
    assert "Inside parent template" in resp
    
def test_template_override():
    app = setup_noDB()
    r =app.get('/template_override')
    assert "Not overridden" in r
    r = app.get('/template_override', params=dict(override=True))
    assert "This is overridden." in r
    # now invoke the controller again without override,
    # it should yield the old result
    r =app.get('/template_override')
    assert "Not overridden" in r


