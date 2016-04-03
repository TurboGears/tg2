# -*- coding: utf-8 -*-
from __future__ import absolute_import

import mimetypes
from ..base import ConfigurationStep, BeforeConfigConfigurationAction


class MimeTypesConfigurationStep(ConfigurationStep):
    """
    """
    id = "mimetypes"

    DEFAULT_PATHS = {
        'root': None,
        'controllers': None,
        'templates': ['.'],
        'static_files': None
    }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_mimetypes),
        )

    def _configure_mimetypes(self, conf, app):
        conf['mimetypes'] = mimetypes.MimeTypes()

        lookup = {'.json': 'application/json',
                  '.js': 'application/javascript'}
        lookup.update(conf.get('mimetype_lookup', {}))

        for key, value in lookup.items():
            conf['mimetypes'].add_type(value, key)


