# -*- coding: utf-8 -*-
import logging
from tg.configuration.utils import coerce_config
from tg.support.converters import asbool, asint, aslist
from ..base import ConfigurationComponent, BeforeConfigConfigurationAction, AppReadyConfigurationAction

log = logging.getLogger(__name__)


class SlowRequestsConfigurationComponent(ConfigurationComponent):
    """Provides slow requests reporting for TurboGears through BackLash.

    This is enabled through the ``trace_slowreqs.enable`` option and
    is only enabled when ``debug=false``.

    All the options available for error reporting are configured
    as ``trace_slowreqs.*`` options in your ``app_cfg`` or ``.ini`` files:

        - ``trace_slowreqs.enable`` -> Enable/Disable slow requests reporting,
          by default it's disabled.
        - ``trace_slowreqs.interval`` -> Report requests slower than this value (default: 25s)
        - ``trace_slowreqs.exclude`` -> List of urls that should be excluded

    Slow requests are reported using *EMail* or *Sentry*, the same
    options available in :class:`.ErrorReportingConfigurationComponent` apply
    with ``trace_slowreqs.`` instead of ``trace_errors.``.

    """
    id = "slow_requests"

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_backlash),
            AppReadyConfigurationAction(self._add_middleware)
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

    def _add_middleware(self, conf, app):
        errorware = conf['tg.slowreqs']
        if errorware.get('enable') and not asbool(conf.get('debug')):
            reporters = []

            if errorware.get('error_email'):
                from backlash.tracing.reporters.mail import EmailReporter
                reporters.append(EmailReporter(**errorware))

            if errorware.get('sentry_dsn'):
                from backlash.tracing.reporters.sentry import SentryReporter
                reporters.append(SentryReporter(**errorware))

            if errorware.get('reporters', []):
                for reporter in errorware['reporters']:
                    reporters.append(reporter)

            try:
                import backlash
            except ImportError:  # pragma: no cover
                log.warning("backlash not installed, slow requests reporting won't be available")
            else:
                return backlash.TraceSlowRequestsMiddleware(
                    app, reporters, interval=errorware.get('interval', 25),
                    exclude_paths=errorware.get('exclude', None),
                    context_injectors=[_turbogears_backlash_context]
                )

        return app


def _turbogears_backlash_context(environ):
    tgl = environ.get('tg.locals')
    return {'request': getattr(tgl, 'request', None)}
