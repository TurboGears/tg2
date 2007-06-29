"""
Definitions for TurboGears quickstart templates
"""
from paste.script import templates

class TurboGearsTemplate(templates.Template):
    egg_plugins = []
    required_templates = []
    _template_dir = 'pastetemplates/turbogears'
    summary = 'TurboGears 2.0 Template'