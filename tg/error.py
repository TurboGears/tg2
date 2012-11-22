import logging
from paste.deploy.converters import asbool

log = logging.getLogger(__name__)

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
        log.warn('backlash not installed, debug mode and email tracebacks won\'t be available')
        return app

    if asbool(global_conf.get('debug')):
        app = backlash.DebuggedApplication(app)
    else:
        from backlash.trace_errors import EmailReporter
        app = backlash.TraceErrorsMiddleware(app, [EmailReporter(**errorware)])

    return app
