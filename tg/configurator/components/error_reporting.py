# -*- coding: utf-8 -*-
import logging

from tg.configuration.utils import coerce_config
from tg.support.converters import asbool, asint
from ..base import ConfigurationComponent, BeforeConfigConfigurationAction, AppReadyConfigurationAction

log = logging.getLogger(__name__)


class ErrorReportingConfigurationComponent(ConfigurationComponent):
    """Provides Error reporting through Backlash on TurboGears.

    This is enabled/disabled through the ``debug`` configuration option.
    Currently EMail and Sentry backlash reporters can be enabled.

    All the options available for error reporting are configured
    as ``trace_errors.*`` options in your ``app_cfg`` or ``.ini`` files.

    The available options for **EMail** reporter are:

        - ``trace_errors.enable`` -> Enable or disable error reporting,
          by default is enabled if backlash is available and ``debug=false``
        - ``trace_errors.smtp_server`` -> SMTP Server to connect to for sending emails
        - ``trace_errors.smtp_port`` -> SMTP port to connect to
        - ``trace_errors.from_address`` -> Address sending the error emails
        - ``trace_errors.error_email`` -> Address the error emails should be sent to.
        - ``trace_errors.smtp_username`` -> Username to authenticate on SMTP server.
        - ``trace_errors.smtp_password`` -> Password to authenticate on SMTP server.
        - ``trace_errors.smtp_use_tls`` -> Whenever to enable or not TLS for SMTP.
        - ``trace_errors.error_subject_prefix`` -> Prefix to append to error emails,
          by default ``WebApp Error:`` is prepended.
        - ``trace_errors.dump_request`` -> Whenever to attach a request dump to the email so that
          all request data is provided.
        - ``trace_errors.dump_request_size`` -> Do not dump request if it's bigger than this value,
          useful for uploaded files. By default 50K.
        - ``trace_errors.dump_local_frames`` -> Enable dumping local variables in case of crashes.
        - ``trace_errors.dump_local_frames_count`` -> Dump up to X frames when dumping local variables.
          The default is 2
        - ``trace_errors.reporters`` -> Add custom reporters to error reporting middleware.

    Available options for **Sentry** reporter are:

        - ``trace_errors.sentry_dsn`` -> Sentry instance where to send the errors.

    """

    id = "error_reporting"

    def get_defaults(self):
        return {
            'debug': False,
            'trace_errors.enable': True
        }

    def get_coercion(self):
        return {
            'debug': asbool
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_backlash),
            AppReadyConfigurationAction(self._add_middleware),
        )

    def _configure_backlash(self, conf, app):
        trace_errors_config = coerce_config(conf, 'trace_errors.', {
            'enable': asbool,
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

    def _add_middleware(self, conf, app):
        errorware = conf['tg.errorware']
        if errorware.get('enable', True) and not asbool(conf.get('debug')):
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
                log.warning("backlash not installed, email tracebacks won't be available")
            else:
                return backlash.TraceErrorsMiddleware(
                    app, reporters, context_injectors=[_turbogears_backlash_context]
                )
        return app


def _turbogears_backlash_context(environ):
    tgl = environ.get('tg.locals')
    return {'request': getattr(tgl, 'request', None)}
