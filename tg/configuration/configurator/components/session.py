# -*- coding: utf-8 -*-
import os

from ...utils import TGConfigError
from ..base import (ConfigurationComponent,
                    BeforeConfigConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class SessionConfigurationComponent(ConfigurationComponent):
    """

    """
    id = 'session'

    def get_defaults(self):
        return {
            'session.enabled': True
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure),
        )

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('Sessions only work on an ApplicationConfigurator')

        from ....appwrappers.session import SessionApplicationWrapper
        configurator.register_application_wrapper(SessionApplicationWrapper, after=True)

    def _configure(self, conf, app):
        if 'cache_dir' in conf:
            conf.setdefault('session.data_dir', os.path.join(conf['cache_dir'], 'sessions'))
