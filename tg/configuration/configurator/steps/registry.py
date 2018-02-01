# -*- coding: utf-8 -*-
from tg.support.converters import asbool
from tg.support.registry import RegistryManager
from ..base import (ConfigurationComponent, AppReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)

__all__ = ('RegistryConfigurationComponent', )


class RegistryConfigurationComponent(ConfigurationComponent):
    """

    """
    id = 'registry'

    def get_coercion(self):
        return {
            'registry_streaming': asbool,
        }

    def get_defaults(self):
        return {
            'registry_streaming': True,
        }

    def get_actions(self):
        return (
            AppReadyConfigurationAction(self._add_registry_middleware),
        )

    def _add_registry_middleware(self, conf, app):
        # Establish the registry for this application
        return RegistryManager(app, streaming=conf.get('registry_streaming', True),
                               preserve_exceptions=conf.get('debug', False))
