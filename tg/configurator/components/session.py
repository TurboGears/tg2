# -*- coding: utf-8 -*-
import os

from ...configuration.utils import TGConfigError
from ..base import (ConfigurationComponent,
                    BeforeConfigConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class SessionConfigurationComponent(ConfigurationComponent):
    """Provide support for sessions through Beaker.

    Session components adds support for setting up the session
    manager used by ``tg.sessions``.

    Options:

        * ``session.enabled``: Add support for sessions in the application.
                               By default sesions are enabled.
        * ``session.data_dir``: Where to store session files, by default
                                the ``$cache_dir/sessions`` is used.

    Refer to :class:`.SessionApplicationWrapper` for all the supported
    options.

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

        from ...appwrappers.session import SessionApplicationWrapper
        configurator.register_application_wrapper(SessionApplicationWrapper, after=True)

    def _configure(self, conf, app):
        if 'cache_dir' in conf:
            conf.setdefault('session.data_dir', os.path.join(conf['cache_dir'], 'sessions'))
