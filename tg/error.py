import logging
from tg.support.converters import asbool

log = logging.getLogger(__name__)


def _turbogears_backlash_context(environ):
    tgl = environ.get('tg.locals')
    return {'request':getattr(tgl, 'request', None)}


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
    try:
        import backlash
    except ImportError: #pragma: no cover
        log.warn('backlash not installed, debug mode won\'t be available')
        return app

    if asbool(global_conf.get('debug')):
        app = backlash.DebuggedApplication(app, context_injectors=[_turbogears_backlash_context])

    return app


def ErrorReporter(app, global_conf, **errorware):
    try:
        import backlash
    except ImportError: #pragma: no cover
        log.warn('backlash not installed, email tracebacks won\'t be available')
        return app

    reporters = []

    if errorware.get('error_email'):
        from backlash.trace_errors import EmailReporter
        reporters.append(EmailReporter(**errorware))

    if errorware.get('sentry_dsn'):
        from backlash.trace_errors.sentry import SentryReporter
        reporters.append(SentryReporter(**errorware))

    if not asbool(global_conf.get('debug')):
        app = backlash.TraceErrorsMiddleware(app, reporters,
                                             context_injectors=[_turbogears_backlash_context])

    return app
