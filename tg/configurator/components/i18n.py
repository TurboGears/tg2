# -*- coding: utf-8 -*-
import os

from ...configuration.utils import TGConfigError
from ...support.converters import aslist
from ..base import (ConfigurationComponent,
                    BeforeConfigConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class I18NConfigurationComponent(ConfigurationComponent):
    """Enable support for internationalization.

    Supported Options:

        * ``i18n.lang``: Default web app language if none was requested or
                         detected from browser. 
                         This will always be listed as fallback language.
        * ``i18n.enabled``: Enable support for translations.
                            Disabling i18n will speedup requests and all
                            pages will be served as they were in ``i18n.lang`` value.
        * ``i18n.native``: Native languages templates are written into. 
                           No translation will occurr for those language.
                           Provide space separated or as a list.
        * ``localedir``: Where to find translation catalogs.
                         By default it's project root/i18n

    Refer to :class:`.I18NApplicationWrapper` for additional options
    in supporting i18n.
    """
    id = 'i18n'

    def get_defaults(self):
        return {
            'i18n.lang': None,
            'i18n.native': None,
            'i18n.enabled': True
        }

    def get_coercion(self):
        return {
            'i18n.native': aslist
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure),
        )

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('I18N only works on an ApplicationConfigurator')

        from ...appwrappers.i18n import I18NApplicationWrapper
        configurator.register_application_wrapper(I18NApplicationWrapper, after=True)

    def _configure(self, conf, app):
        if conf['paths']['root']:
            conf['localedir'] = os.path.join(conf['paths']['root'], 'i18n')
        else:
            conf['i18n.enabled'] = False
