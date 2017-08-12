import logging
from tg.support.converters import asbool

log = logging.getLogger(__name__)


def _turbogears_backlash_context(environ):
    tgl = environ.get('tg.locals')
    return {'request': getattr(tgl, 'request', None)}


def ErrorHandler(app, global_conf, **errorware):
    """ErrorHandler Toggle

    If debug is enabled, this function will return the app wrapped in
    the WebError ``EvalException`` middleware which displays
    interactive debugging sessions when a traceback occurs.

    Otherwise, the app will be wrapped in the WebError
    ``ErrorMiddleware``, and the ``errorware`` dict will be passed into
    it. The ``ErrorMiddleware`` handles sending an email to the address
    listed in the .ini file, under ``email_to``.

    """

    if asbool(global_conf.get('debug')):

        try:
            import backlash
        except ImportError:  #pragma: no cover
            log.warning('backlash not installed,'
                        ' debug mode won\'t be available')
        else:
            app = backlash.DebuggedApplication(
                app, context_injectors=[_turbogears_backlash_context])

    return app


def ErrorReporter(app, global_conf, **errorware):
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

    Available options for **Sentry** reporter are:

        - ``trace_errors.sentry_dsn`` -> Sentry instance where to send the errors.

    """

    if errorware.get('enable', True) and not asbool(global_conf.get('debug')):

        reporters = []

        if errorware.get('error_email'):
            from backlash.tracing.reporters.mail import EmailReporter
            reporters.append(EmailReporter(**errorware))

        if errorware.get('sentry_dsn'):
            from backlash.tracing.reporters.sentry import SentryReporter
            reporters.append(SentryReporter(**errorware))

        try:
            import backlash
        except ImportError:  #pragma: no cover
            log.warning('backlash not installed,'
                        ' email tracebacks won\'t be available')
        else:
            app = backlash.TraceErrorsMiddleware(
                app, reporters,
                context_injectors=[_turbogears_backlash_context])

    return app


def SlowReqsReporter(app, global_conf, **errorware):
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
    options available in :class:`.ErrorReporter` apply with ``trace_slowreqs.``
    instead of ``trace_errors.``.

    """
    if errorware.get('enable') and not asbool(global_conf.get('debug')):

        reporters = []

        if errorware.get('error_email'):
            from backlash.tracing.reporters.mail import EmailReporter
            reporters.append(EmailReporter(**errorware))

        if errorware.get('sentry_dsn'):
            from backlash.tracing.reporters.sentry import SentryReporter
            reporters.append(SentryReporter(**errorware))

        try:
            import backlash
        except ImportError:  #pragma: no cover
            log.warning('backlash not installed,'
                        ' slow requests reporting won\'t be available')
        else:
            app = backlash.TraceSlowRequestsMiddleware(
                app, reporters, interval=errorware.get('interval', 25),
                exclude_paths=errorware.get('exclude', None),
                context_injectors=[_turbogears_backlash_context])

    return app
