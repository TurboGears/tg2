# -*- coding: utf-8 -*-

import tg
from tests.test_stack import TestConfig, app_from_config
from tg.util import Bunch
from webtest import TestApp
from pylons import tmpl_context

def setup_noDB(genshi_doctype=None, genshi_method=None, genshi_encoding=None):
    base_config = TestConfig(folder='rendering', values={
        'use_sqlalchemy': False,
       'pylons.helpers': Bunch(),
       'use_legacy_renderer': False,
       # this is specific to mako  to make sure inheritance works
       'use_dotted_templatenames': False,
       'pylons.tmpl_context_attach_args': False
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

    return app_from_config(base_config, deployment_config)

def test_default_genshi_renderer():
    app = setup_noDB()
    resp = app.get('/')
    assert ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">') in resp
    assert "Welcome" in resp
    assert "TurboGears" in resp

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
    app = setup_noDB()
    resp = app.get('/chameleon_genshi_index')
    assert ("<p>TurboGears 2 is rapid web application development toolkit"
        " designed to make your life easier.</p>") in resp

def test_chameleon_genshi_inheritance():
    try:
        import lxml
    except ImportError:
        # match templates need lxml, but since they don're really work anyway
        # (at least not fully compatible with Genshi), we just skip this test
        return
    app = setup_noDB()
    try:
        resp = app.get('/chameleon_genshi_inherits')
    except NameError, e:
        # known issue with chameleon.genshi 1.0
        if 'match_templates' not in str(e):
            raise
    except AttributeError, e:
        # known issue with chameleon.genshi 1.3
        if 'XPathResult' not in str(e):
            raise
    else:
        assert "Inheritance template" in resp
        assert "Master template" in resp

def _test_jinja_inherits():
    app = setup_noDB()
    resp = app.get('/jinja_inherits')
    assert "Welcome on my awsome homepage" in resp, resp

def test_jinja_extensions():
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['jinja'],
                                       'jinja_extensions': ['jinja2.ext.do', 'jinja2.ext.i18n',
                                                            'jinja2.ext.with_', 'jinja2.ext.autoescape']
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
        string_hash = md5(value)
        return string_hash.hexdigest()

    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': False,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['jinja'],
                                       'jinja_filters': {'codify': codify}
                                       }
                             )
    app = app_from_config(base_config)
    resp = app.get('/jinja_filters')
    assert '8bb23e0b574ecb147536efacc864891b' in resp, resp

def test_jinja_autoload_filters():
    app = setup_noDB()
    resp = app.get('/jinja_filters')
    assert '29464d5ffe8f8dba1782fffcd6ed9fca6ceb4742' in resp, resp

def test_mako_renderer():
    app = setup_noDB()
    resp = app.get('/mako_index')
    assert "<p>This is the mako index page</p>" in resp, resp

def test_mako_inheritance():
    app = setup_noDB()
    resp = app.get('/mako_inherits')
    assert "inherited mako page" in resp, resp
    assert "Inside parent template" in resp, resp

def test_template_override():
#    app = setup_noDB()
    base_config = TestConfig(folder = 'rendering',
                             values = {'use_sqlalchemy': False,
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['genshi']
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
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['genshi']
                                       }
                             )
    app = app_from_config(base_config)
    r = app.get('/template_override_wts', status=302) # ensure with_trailing_slash
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
                                       'pylons.helpers': Bunch(),
                                       'use_legacy_renderer': False,
                                       # this is specific to mako
                                       # to make sure inheritance works
                                       'use_dotted_templatenames': True,
                                       'pylons.tmpl_context_attach_args': False,
                                       'renderers':['mako', 'genshi']
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

def test_template_override_multiple_content_type():
    app = setup_noDB()
    resp = app.get('/template_override_multiple_content_type')
    assert 'something' in resp

    resp = app.get(
        '/template_override_multiple_content_type',
        params=dict(override=True))
    assert 'This is the mako index page' in resp

def test_jinja2_manual_rendering():
    app = setup_noDB()
    tgresp = app.get('/jinja2_manual_rendering')
    pyresp = app.get('/jinja2_manual_rendering?frompylons=1')
    assert str(tgresp) == str(pyresp)

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
