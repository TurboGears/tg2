import tg.renderers.json


class FakePackage(object):
    __file__ = __file__
FakePackage.__name__ = 'tests'


default_config = {
        'debug': False,
        'package': FakePackage,
        'package_name' : 'tests',
        'paths': {'root': '.',
                  'controllers': '.',
                  'templates': [],
                  'static_files': None},
        'db_engines': {},
        'tg.strict_tmpl_context':False,
        'use_dotted_templatenames':True,
        'buffet.template_engines': [],
        'buffet.template_options': {},
        'default_renderer':'json',
        'renderers': ['json'],
        'render_functions': {'json': tg.renderers.json.JSONRenderer.render_json},
        'rendering_engines_options': {'json': {'content_type': 'application/json'}},
        'rendering_engines_without_vars': set(('json',)),
        'use_legacy_renderers': False,
        'use_sqlalchemy': False,
        'i18n.lang': None
}


class ControllerWrap(object):
    def __init__(self, controller):
        self.controller = controller

    def __call__(self, environ, start_response):
        app = self.controller()
        return app(environ, start_response)
