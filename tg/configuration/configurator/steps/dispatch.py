# -*- coding: utf-8 -*-
from ..base import ConfigurationStep, BeforeConfigConfigurationAction

from logging import getLogger
log = getLogger(__name__)


class DispatchConfigurationStep(ConfigurationStep):
    """
        - root_controller
        - disable_request_extensions
        - dispatch_path_translator
        - ignore_parameters
        - enable_routing_args
    """
    id = "dispatch"

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_explicit_root_controller),
        )

    def _configure_explicit_root_controller(self, conf, app):
        conf['tg.root_controller'] = conf.pop('root_controller', None)
