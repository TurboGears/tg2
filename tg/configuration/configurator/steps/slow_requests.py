# -*- coding: utf-8 -*-
from tg.configuration.utils import coerce_config
from tg.support.converters import asbool, asint, aslist
from ..base import ConfigurationStep, BeforeConfigConfigurationAction


class SlowRequestsConfigurationStep(ConfigurationStep):
    """

    """
    id = "slow_requests"

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_backlash),
        )

    def _configure_backlash(self, conf, app):
        slowreqsware = coerce_config(conf, 'trace_slowreqs.', {'smtp_use_tls': asbool,
                                                               'dump_request_size': asint,
                                                               'dump_request': asbool,
                                                               'dump_local_frames': asbool,
                                                               'dump_local_frames_count': asint,
                                                               'enable': asbool,
                                                               'interval': asint,
                                                               'exclude': aslist})

        slowreqsware.setdefault('error_subject_prefix', 'Slow Request: ')
        slowreqsware.setdefault('error_message', 'A request is taking too much time')

        errorware = conf.get('tg.errorware', {})
        for erroropt in errorware:
            slowreqsware.setdefault(erroropt, errorware[erroropt])
        conf['tg.slowreqs'] = slowreqsware