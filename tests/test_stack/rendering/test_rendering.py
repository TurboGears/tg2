# -*- coding: utf-8 -*-
from nose import SkipTest
import shutil, os
import json
import tg
from tg.configuration import milestones
#tg.configuration.reqlocal_config.push_process_config({})

from tests.test_stack import TestConfig, app_from_config
from tg.configuration.hooks import _TGGlobalHooksNamespace
from tg.util import Bunch
from tg._compat import PY3, im_func
from tg.renderers.genshi import GenshiRenderer
from tg import expose
from tg import TGController, AppConfig
from webtest import TestApp
from datetime import datetime

try:
    from tgext.chameleon_genshi import ChameleonGenshiRenderer
except ImportError:
    ChameleonGenshiRenderer = None

def setup_noDB(genshi_doctype=None, genshi_method=None, genshi_encoding=None, extra={},
               extra_init=None):
    base_config = TestConfig(folder='rendering', values={
        'use_sqlalchemy': False,
       'use_legacy_renderer': False,
       # this is specific to mako  to make sure inheritance works
       'use_dotted_templatenames': False,
       'use_toscawidgets': False,
       'use_toscawidgets2': False
    })

    deployment_config = {}
    # remove previous option value to avoid using the old one
    tg.config.pop('templating.genshi.doctype', None)
    if genshi_doctype:
        deployment_config['templating.genshi.doctype'] = genshi_doctype
    tg.config.pop('templating.genshi.method', None)
    if genshi_method:
        deployment_config['templating.genshi.method'] = genshi_method
    tg.config.pop('templating.genshi.encoding', None)
    if genshi_encoding:
        deployment_config['templating.genshi.encoding'] = genshi_encoding

    deployment_config.update(extra)

    if extra_init is not None:
        extra_init(base_config)

    return app_from_config(base_config, deployment_config)

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_genshi_nameconstant():
    from genshi.template.astutil import ASTCodeGenerator, parse
    from tg.renderers.genshi import GenshiRenderer

    # This checks genshi gets monkeypatched to fix it on Py34 if option is provided
    GenshiRenderer.create(Bunch({
        'templating.genshi.name_constant_patch': True,
        'use_dotted_templatenames': False,
        'auto_reload_templates': False,
        'paths': Bunch({'templates': '/tmp'})
    }), None)
    assert hasattr(ASTCodeGenerator, 'visit_NameConstant')

    astgen = ASTCodeGenerator(parse('range(10)', mode='eval'))
    for n in (False, True, None):
        astgen._new_line()
        astgen.visit_NameConstant(Bunch(value=n))
        line = str(astgen.line)
        assert line == str(n), line

    astgen._new_line()
    try:
        astgen.visit_NameConstant(Bunch(value='HELLO_WORLD'))
    except Exception as e:
        assert 'Unknown NameConstant' in str(e)
    else:
        assert False

def test_genshi_doctype_html5():
    app = setup_noDB(genshi_doctype='html5')
    resp = app.get('/')
    assert '<!DOCTYPE html>' in resp
    assert "Welcome" in resp
    assert "TurboGears" in resp

def test_genshi_auto_doctype():
    app = setup_noDB()
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_html():
    app = setup_noDB(genshi_method='html')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"'
        ' "http://www.w3.org/TR/html4/loose.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xhtml():
    app = setup_noDB(genshi_method='xhtml')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_html():
    app = setup_noDB(genshi_doctype='html')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_html5():
    app = setup_noDB(genshi_doctype='html5')
    resp = app.get('/auto_doctype')
    assert '<!DOCTYPE html>' in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_xhtml_strict():
    app = setup_noDB(genshi_doctype='xhtml-strict')
    resp = app.get('/auto_doctype')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_html_maps_to_xhtml():
    app = setup_noDB(genshi_doctype={'text/html': ('xhtml', 'html')})
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_html_maps_to_xhtml():
    app = setup_noDB(genshi_method={'text/html': ('xhtml', 'html')})
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xml_overridden_by_content_type_html():
    app = setup_noDB(genshi_method='xml')
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xhtml_is_ok_with_content_type_html():
    app = setup_noDB(genshi_method='xhtml')
    resp = app.get('/auto_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_doctype_xhtml_maps_to_html():
    app = setup_noDB(
        genshi_doctype={'application/xhtml+xml': ('html', 'xhtml')})
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xhtml_maps_to_html():
    app = setup_noDB(
        genshi_doctype={'application/xhtml+xml': ('html', 'xhtml')},
        genshi_method={'application/xhtml+xml': ('html', 'xhtml')})
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_xml_overridden_by_content_type_xhtml():
    app = setup_noDB(genshi_method='xml')
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_method_html_overridden_by_content_type_xhtml():
    app = setup_noDB(genshi_method='html')
    resp = app.get('/auto_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="application/xhtml+xml; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_explicit_no_doctype():
    app = setup_noDB()
    resp = app.get('/explicit_no_doctype')
    assert 'DOCTYPE' not in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_explicit_doctype_html():
    app = setup_noDB(genshi_doctype='xhtml')
    resp = app.get('/explicit_doctype_html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_explicit_doctype_xhtml():
    app = setup_noDB(genshi_doctype='html')
    resp = app.get('/explicit_doctype_xhtml')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "doctype generation" in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_html_priority_for_ie():
    app = setup_noDB()
    resp = app.get('/html_and_json', headers={'Accept':
        'application/x-ms-application, image/jpeg, application/xaml+xml,'
        ' image/gif, image/pjpeg, application/x-ms-xbap, */*'})
    assert 'text/html' in str(resp), resp

def test_genshi_foreign_characters():
    app = setup_noDB()
    resp = app.get('/foreign')
    assert "Foreign Cuisine" in resp
    assert "Crème brûlée with Käsebrötchen" in resp

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
    if ChameleonGenshiRenderer is None:
        raise SkipTest()

    def add_chameleon_renderer(app_config):
        app_config.register_rendering_engine(ChameleonGenshiRenderer)
        app_config.renderers.append('chameleon_genshi')

    app = setup_noDB(extra_init=add_chameleon_renderer)

    # Manually add the exposition again as it was already discarded
    # due to chameleon_genshi not being in the available renderes.
    milestones.renderers_ready._reset()
    from .controllers.root import RootController
    controller = im_func(RootController.chameleon_genshi_index)
    expose('chameleon_genshi:index.html')(controller)
    milestones.renderers_ready.reach()

    resp = app.get('/chameleon_genshi_index')
    assert ("<p>TurboGears 2 is rapid web application development toolkit"
        " designed to make your life easier.</p>") in resp

def test_chameleon_genshi_inheritance():
    if ChameleonGenshiRenderer is None:
        raise SkipTest()

    def add_chameleon_renderer(app_config):
        app_config.register_rendering_engine(ChameleonGenshiRenderer)
        app_config.renderers.append('chameleon_genshi')

    try:
        import lxml
    except ImportError:
        # match templates need lxml, but since they don're really work anyway
        # (at least not fully compatible with Genshi), we just skip this test
        return

    app = setup_noDB(extra_init=add_chameleon_renderer)

    milestones.renderers_ready._reset()
    from .controllers.root import RootController
    controller = im_func(RootController.chameleon_genshi_inherits)
    expose('chameleon_genshi:genshi_inherits.html')(controller)
    milestones.renderers_ready.reach()

    try:
        resp = app.get('/chameleon_genshi_inherits')
    except NameError as e:
        # known issue with chameleon.genshi 1.0
        if 'match_templates' not in str(e):
            raise
    except AttributeError as e:
        # known issue with chameleon.genshi 1.3
        if 'XPathResult' not in str(e):
            raise
    else:
        assert "Inheritance template" in resp
        assert "Master template" in resp

def test_jinja_autoload():
    app = setup_noDB()

    try:
        resp = app.get('/jinja_autoload')
        assert False
    except Exception as e:
        assert "no filter named 'polluting_function'" in str(e)

def _test_jinja_inherits():
    app = setup_noDB()
    resp = app.get('/jinja_inherits')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_extensions():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'renderers':['jinja'],
                                       'jinja_extensions': ['jinja2.ext.do', 'jinja2.ext.i18n',
                                                            'jinja2.ext.with_', 'jinja2.ext.autoescape'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    resp = app.get('/jinja_extensions')
    assert "<b>Autoescape Off</b>" in resp, resp
    assert "&lt;b&gt;Test Autoescape On&lt;/b&gt;" in resp, resp

def test_jinja_buildin_filters():
    app = setup_noDB()
    resp = app.get('/jinja_buildins')
    assert 'HELLO JINJA!' in resp, resp

def test_jinja_custom_filters():
    # Simple test filter to get a md5 hash of a string
    def codify(value):
        try:
            from hashlib import md5
        except ImportError:
            from md5 import md5
        string_hash = md5(value.encode('ascii'))
        return string_hash.hexdigest()

    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'renderers':['jinja'],
                                       'jinja_filters': {'codify': codify},
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)

    try:
        resp = app.get('/jinja_filters')
    finally:
        # Remove filters so we don't mess with other test units
        tg.config.pop('jinja_filters')

    assert '8bb23e0b574ecb147536efacc864891b' in resp, resp

def test_jinja_autoload_filters():
    app = setup_noDB()
    resp = app.get('/jinja_filters')
    assert '29464d5ffe8f8dba1782fffcd6ed9fca6ceb4742' in resp, resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index')
    assert "<p>This is the mako index page</p>" in resp, resp

def test_mako_renderer_compiled():
    app = setup_noDB(extra={
        'templating.mako.compiled_templates_dir': '_tg_tests_mako_compiled/dest'
    })

    resp = app.get('/mako_index')
    assert "<p>This is the mako index page</p>" in resp, resp

    assert os.path.exists('_tg_tests_mako_compiled')
    shutil.rmtree('_tg_tests_mako_compiled', True)

def test_mako_renderer_compiled_existing():
    os.makedirs('_tg_tests_mako_compiled/dest')
    test_mako_renderer_compiled()

def test_mako_renderer_compiled_no_access():
    os.makedirs('_tg_tests_mako_compiled')
    os.makedirs('_tg_tests_mako_compiled/dest', mode=0o400)
    test_mako_renderer_compiled()

def test_mako_renderer_compiled_no_access_parent():
    os.makedirs('_tg_tests_mako_compiled', mode=0o400)
    test_mako_renderer_compiled()

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits')
    assert "inherited mako page" in resp, resp
    assert "Inside parent template" in resp, resp

def test_template_override():
#    app = setup_noDB()
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'renderers':['genshi'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    r =app.get('/template_override')
    assert "Not overridden" in r, r
    r = app.get('/template_override', params=dict(override=True))
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override')
    assert "Not overridden" in r, r

def test_template_override_wts():
#    app = setup_noDB()
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'renderers':['genshi'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    r = app.get('/template_override_wts', status=301) # ensure with_trailing_slash
    r =app.get('/template_override_wts/')
    assert "Not overridden" in r, r
    r = app.get('/template_override_wts/', params=dict(override=True))
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override_wts/')
    assert "Not overridden" in r, r

def test_template_override_content_type():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'renderers':['mako', 'genshi'],
                                       'use_toscawidgets': False,
                                       'use_toscawidgets2': False
                                       }
                             )
    app = app_from_config(base_config)
    r =app.get('/template_override_content_type')
    assert r.content_type == 'text/javascript'
    assert "Not overridden" in r, r
    r = app.get('/template_override_content_type', params=dict(override=True))
    assert r.content_type == 'text/javascript'
    assert "This is overridden." in r, r
    # now invoke the controller again without override,
    # it should yield the old result
    r = app.get('/template_override_content_type')
    assert "Not overridden" in r, r

def test_template_custom_format_default():
    app = setup_noDB()
    resp = app.get('/custom_format')
    assert 'OK' in resp
    assert resp.content_type == 'text/html'

def test_template_custom_format_xml():
    app = setup_noDB()
    resp = app.get('/custom_format?format=xml')
    assert 'xml' in resp
    assert resp.content_type == 'text/xml'

def test_template_custom_format_json():
    app = setup_noDB()
    resp = app.get('/custom_format?format=json')
    assert 'json' in resp
    assert resp.content_type == 'application/json'

def test_template_custom_format_html():
    app = setup_noDB()
    resp = app.get('/custom_format?format=html')
    assert 'html' in resp
    assert resp.content_type == 'text/html'

def test_template_custom_format_nonexisting():
    app = setup_noDB()

    try:
        resp = app.get('/custom_format?format=csv')
        assert False
    except Exception as e:
        assert 'not a valid custom_format' in str(e)

def test_template_override_multiple_content_type():
    app = setup_noDB()
    resp = app.get('/template_override_multiple_content_type')
    assert 'something' in resp

    resp = app.get(
        '/template_override_multiple_content_type',
        params=dict(override=True))
    assert 'This is the mako index page' in resp

def test_override_template_on_noncontroller():
    tg.override_template(None, 'this.is.not.a.template')

def test_jinja2_manual_rendering():
    app = setup_noDB()
    tgresp = app.get('/jinja2_manual_rendering')
    pyresp = app.get('/jinja2_manual_rendering?frompylons=1')
    assert str(tgresp) == str(pyresp), str(tgresp) + '\n------\n' + str(pyresp)

def test_no_template():
    app = setup_noDB()
    resp = app.get('/no_template_generator')
    assert '1234' in resp, resp

def test_genshi_manual_render_no_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype')
    assert 'DOCTYPE' not in resp, resp
    assert "<hr />" in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_manual_render_auto_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype?doctype=auto')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "<hr />" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_manual_render_html_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype?doctype=html')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01//EN"'
        ' "http://www.w3.org/TR/html4/strict.dtd">') in resp
    assert 'content="text/html; charset=utf-8"' in resp
    assert "<hr>" in resp
    assert "<p>Rendered with Genshi.</p>" in resp

def test_genshi_manual_render_svg_doctype():
    app = setup_noDB()
    resp = app.get('/genshi_manual_rendering_with_doctype?doctype=svg')
    assert '<!DOCTYPE svg' in resp

def test_genshi_methods_for_doctype():
    assert GenshiRenderer.method_for_doctype('application/xml') == 'xhtml'

def test_variable_provider():
    app = setup_noDB(extra={'variable_provider': lambda: {'inject_this_var':5}})
    resp = app.get('/get_tg_vars')
    assert 'inject_this_var' in resp

def test_render_hooks():
    old_hooks, tg.hooks = tg.hooks, _TGGlobalHooksNamespace()

    calls = []
    def render_call_hook(*args, **kw):
        calls.append(1)

    base_config = TestConfig(folder='rendering', values={
        'use_sqlalchemy': False,
        'use_legacy_renderer': False,
        # this is specific to mako  to make sure inheritance works
        'use_dotted_templatenames': False,
        'use_toscawidgets': False,
        'use_toscawidgets2': False
    })

    milestones._reset_all()
    base_config.register_hook('before_render_call', render_call_hook)
    base_config.register_hook('after_render_call', render_call_hook)
    app = app_from_config(base_config, reset_milestones=False)
    app.get('/')

    try:
        assert len(calls) == 2
    finally:
        tg.hooks = old_hooks

class TestTemplateCaching(object):
    def setUp(self):
        base_config = TestConfig(folder='rendering', values={
            'use_sqlalchemy': False,
            'use_legacy_renderer': False,
            # this is specific to mako  to make sure inheritance works
            'use_dotted_templatenames': False,
            'use_toscawidgets': False,
            'use_toscawidgets2': False,
            'cache_dir': '.'
        })
        self.app = app_from_config(base_config)

    def test_basic(self):
        resp = self.app.get('/template_caching')
        current_date = resp.text.split('NOW:')[1].split('\n')[0].strip()

        resp = self.app.get('/template_caching')
        assert current_date in resp, (current_date, resp.body)

    def test_default_type(self):
        resp = self.app.get('/template_caching_default_type')
        current_date = resp.text.split('NOW:')[1].split('\n')[0].strip()

        resp = self.app.get('/template_caching_default_type')
        assert current_date in resp, (current_date, resp.body)

    def test_template_caching_options(self):
        resp = self.app.get('/template_caching_options', params={'cache_type':'memory'})
        resp = json.loads(resp.text)
        assert resp['cls'] == 'MemoryNamespaceManager', resp

        resp = self.app.get('/template_caching_options', params={'cache_expire':1})
        resp = json.loads(resp.text)
        assert resp['cls'] == 'NoImplementation', resp

        resp = self.app.get('/template_caching_options', params={'cache_key':'TEST'})
        resp = json.loads(resp.text)
        assert resp['cls'] == 'NoImplementation', resp


class TestJSONRendering(object):
    def setUp(self):
        base_config = TestConfig(folder='rendering', values={
            'use_sqlalchemy': False,
            'use_legacy_renderer': False,
            # this is specific to mako  to make sure inheritance works
            'use_dotted_templatenames': False,
            'use_toscawidgets': False,
            'use_toscawidgets2': False,
            'cache_dir': '.',
            'json.isodates': True
        })
        self.app = app_from_config(base_config)

    def teardown(self):
        milestones._reset_all()

    def test_jsonp(self):
        resp = self.app.get('/get_jsonp', params={'call': 'callme'})
        assert 'callme({"value": 5});' in resp.text, resp

    def test_jsonp_missing_callback(self):
        resp = self.app.get('/get_jsonp', status=400)
        assert 'JSONP requires a "call" parameter with callback name' in resp.text, resp

    def test_json_isodates_default(self):
        resp = self.app.get('/get_json_isodates_default')
        assert 'T' in resp.json_body['date']
        assert resp.json_body['date'].startswith(datetime.utcnow().strftime('%Y-%m-%d'))

    def test_json_isodates(self):
        resp = self.app.get('/get_json_isodates_on')
        assert 'T' in resp.json_body['date']
        assert resp.json_body['date'].startswith(datetime.utcnow().strftime('%Y-%m-%d'))

    def test_json_without_isodates(self):
        resp = self.app.get('/get_json_isodates_off')
        assert ' ' in resp.json_body['date'], resp
