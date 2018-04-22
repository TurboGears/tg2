# -*- coding: utf-8 -*-
from __future__ import absolute_import

import mimetypes
from ..base import ConfigurationComponent, BeforeConfigConfigurationAction


class MimeTypesConfigurationComponent(ConfigurationComponent):
    """Configure known MimeTypes.

    Mimetypes are used by turbogears to detect expected content
    types based on file extensions. For example it's used by
    :class:`.DispatchConfigurationComponent` request extensions
    to serve the right content based on URL path extension.

    Options:

        * ``mimetype_lookup``: Additional mapping from extensions to
                               mimetypes that should be configured.
    """
    id = "mimetypes"

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


