"""Definitions for TurboGears quickstart templates"""
from paste.script import templates

class TurboGearsTemplate(templates.Template):
    egg_plugins = ['TurboGears2', 'Pylons', 'WebHelpers']
    required_templates = []
    _template_dir = 'templates/turbogears'
    summary = 'TurboGears 2.0 Template'
    
    def pre(self, command, output_dir, vars):
        """Called before template is applied."""
        package_logger = vars['package']
        if package_logger == 'root':
           # Rename the app logger in the rare case a project is named 'root'
           package_logger = 'app'
        vars['package_logger'] = package_logger

        template_engine = vars.setdefault('template_engine', 'genshi')

        vars['babel_templates_extractor'] = ''