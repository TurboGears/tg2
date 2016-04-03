# -*- coding: utf-8 -*-
import os
from ..configurator import ConfigurationStep, BeforeConfigConfigurationAction


class CachingConfigurationStep(ConfigurationStep):
    """

    """
    id = 'caching'

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_caching),
        )

    def _configure_caching(self, conf, app):
        # Copy in some defaults
        if 'cache_dir' in conf:
            conf.setdefault('session.data_dir', os.path.join(conf['cache_dir'], 'sessions'))
            conf.setdefault('cache.data_dir', os.path.join(conf['cache_dir'], 'cache'))
        conf['tg.cache_dir'] = conf.pop('cache_dir', conf['app_conf'].get('cache_dir'))