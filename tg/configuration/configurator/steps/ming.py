# -*- coding: utf-8 -*-
from ..base import ConfigurationStep, BeforeConfigConfigurationAction


class MingConfigurationStep(ConfigurationStep):
    """
    """
    id = "ming"

    DEFAULT_PATHS = {
        'root': None,
        'controllers': None,
        'templates': ['.'],
        'static_files': None
    }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_ming),
        )

    def _configure_ming(self, conf, app):
        try:
            autoflush_enabled = conf['ming.autoflush']
        except KeyError:
            autoflush_enabled = True

        conf['ming.autoflush'] = conf.get('use_ming', False) and autoflush_enabled