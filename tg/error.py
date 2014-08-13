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

    if not asbool(global_conf.get('debug')):

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
