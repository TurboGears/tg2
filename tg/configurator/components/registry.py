# -*- coding: utf-8 -*-
from tg.support.converters import asbool
from tg.support.registry import RegistryManager
from ..base import (ConfigurationComponent, AppReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)

__all__ = ('RegistryConfigurationComponent', )


class RegistryConfigurationComponent(ConfigurationComponent):
    """Configure the request local context registry.

    This configures support for setting and restoring a clean
    turbogears context on each request. This makes so that
    ``tg.request``, ``tg.response`` and so on always refer to
    the data for current request.

    Options:

        * ``registry_streaming``: Enable streaming responses, thus restoring
                                  the registry at the end of the stream instead of
                                  as soon as the controller action returned.
                                  This is enabled by default.
        * ``debug``: Ensures that the registry is not discarded in case of an
                     exception. So that after the exception is possible to inspect
                     the state of the request that caused the exception.

    """
    id = 'registry'

    def get_coercion(self):
        return {
            'registry_streaming': asbool,
            'debug': asbool
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
