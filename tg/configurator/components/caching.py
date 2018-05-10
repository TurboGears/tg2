# -*- coding: utf-8 -*-
import os

from ...support.converters import asbool
from ...configuration.utils import TGConfigError
from ..base import ConfigurationComponent, BeforeConfigConfigurationAction


class CachingConfigurationComponent(ConfigurationComponent):
    """Provide support for caching through Beaker.

    Caching components adds support for setting up the cache
    manager used by all caching features of turbogears:

        * The tg.cache object.
        * Templates caching
        * function results caching by key
        * Controller actions caching.

    Supported Options:

        * ``cache.enabled``: Enabled/Disable caching, by default True.

    Refer to :class:`.CacheApplicationWrapper` for additional options.
    """
    id = 'caching'

    def get_defaults(self):
        return {
            'cache.enabled': True
        }

    def get_coercion(self):
        return {
            'cache.enabled': asbool
        }

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('Caching only works on an ApplicationConfigurator')

        from ...appwrappers.caching import CacheApplicationWrapper
        configurator.register_application_wrapper(CacheApplicationWrapper, after=True)

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_caching),
        )

    def _configure_caching(self, conf, app):
        if 'cache_dir' in conf:
            conf.setdefault('cache.data_dir', os.path.join(conf['cache_dir'], 'cache'))
