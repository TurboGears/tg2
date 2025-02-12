import os

from webtest import TestApp

import tests
import tg
from tg import AppConfig
from tg._compat import PY3
from tg.configuration import milestones
from tg.util import DottedFileNameFinder


class TestConfig(AppConfig):
    __test__ = False

    def __init__(self, folder, values=None):
        if values is None:
            values = {}
        AppConfig.__init__(self)

        # First we setup some base values that we know will work
        self.renderers = ['genshi', 'mako', 'jinja','json', 'jsonp', 'kajiki']
        self.render_functions = tg.util.Bunch()
        self.package = tests.test_stack
        self.default_renderer = 'kajiki'
        self.globals = self
        self["sa_auth.enabled"] = False
        self.auto_reload_templates = False
        self.use_legacy_renderer = False
        self.use_dotted_templatenames = False
        self.serve_static = False
        self['errorpage.enabled'] = False
        self['trace_errors.enable'] = False
        self['trace_slowreqs.enable'] = False

        root = os.path.dirname(os.path.dirname(tests.__file__))
        test_base_path = os.path.join(root,'tests', 'test_stack',)
        test_config_path = os.path.join(test_base_path, folder)
        self.paths = tg.util.Bunch(
            root=test_base_path,
            controllers=os.path.join(test_config_path, 'controllers'),
            static_files=os.path.join(test_config_path, 'public'),
            templates=[os.path.join(test_config_path, 'templates')],
            i18n=os.path.join(test_config_path, 'i18n')
        )

        # then we override those values with what was passed in
        for key, value in values.items():
            setattr(self, key, value)


def app_from_config(base_config, deployment_config=None, reset_milestones=True):
    if not deployment_config:
        deployment_config = {'debug': 'false',
                             'error_email_from': 'paste@localhost',
                             'smtp_server': 'localhost'}

    # Reset milestones so that they can be reached again
    # on next configuration initialization\
    if reset_milestones:
        milestones._reset_all()

    app = TestApp(base_config.make_wsgi_app(**deployment_config))
    return app



