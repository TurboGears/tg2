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

    if not asbool(global_conf.get('debug')):
        return app

    try:
        from backlash import DebuggedApplication
        app = DebuggedApplication(app)
    except ImportError:
        log.warn('backlash not installed while debug mode enabled, skipping debug mode')

    return app
