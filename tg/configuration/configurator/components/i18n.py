# -*- coding: utf-8 -*-
import os

from ...utils import TGConfigError
from ..base import (ConfigurationComponent,
                    BeforeConfigConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class I18NConfigurationComponent(ConfigurationComponent):
    """

    """
    id = 'i18n'

    def get_defaults(self):
        return {
            'i18n.lang': None,
            'i18n.enabled': True
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure),
        )

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('I18N only works on an ApplicationConfigurator')

        from ....appwrappers.i18n import I18NApplicationWrapper
        configurator.register_application_wrapper(I18NApplicationWrapper, after=True)

    def _configure(self, conf, app):
        if conf['paths']['root']:
            conf['localedir'] = os.path.join(conf['paths']['root'], 'i18n')
        else:
            conf['i18n.enabled'] = False
