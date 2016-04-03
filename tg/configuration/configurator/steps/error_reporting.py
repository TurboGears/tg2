# -*- coding: utf-8 -*-
from tg.configuration.utils import coerce_config
from tg.support.converters import asbool, asint
from ..base import ConfigurationStep, BeforeConfigConfigurationAction


class ErrorReportingConfigurationStep(ConfigurationStep):
    """

    """
    id = "error_reporting"

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_backlash),
        )

    def _configure_backlash(self, conf, app):

        trace_errors_config = coerce_config(conf, 'trace_errors.', {
            'smtp_use_tls': asbool,
            'dump_request_size': asint,
            'dump_request': asbool,
            'dump_local_frames': asbool,
            'dump_local_frames_count': asint
        })

        trace_errors_config.setdefault('debug', conf.get('debug', False))
        trace_errors_config.setdefault('error_subject_prefix', 'WebApp Error: ')
        trace_errors_config.setdefault('error_message', 'An internal server error occurred')
        conf['tg.errorware'] = trace_errors_config