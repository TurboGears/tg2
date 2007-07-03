"""
Definitions for TurboGears quickstart templates
"""
from paste.script import templates

class TurboGearsTemplate(templates.Template):
    egg_plugins = ['TurboGears2', 'Pylons', 'WebHelpers']
    required_templates = []
    _template_dir = 'templates/turbogears'
    summary = 'TurboGears 2.0 Template'