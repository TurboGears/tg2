import logging
from paste.deploy.converters import asbool

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

    from backlash.trace_errors import EmailReporter
    if not asbool(global_conf.get('debug')):
        app = backlash.TraceErrorsMiddleware(app, [EmailReporter(**errorware)],
                                             context_injectors=[_turbogears_backlash_context])

    return app
