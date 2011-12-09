from paste.deploy.converters import asbool
from weberror.evalexception import EvalException
from weberror.errormiddleware import ErrorMiddleware

report_libs = ['TurboGears', 'genshi', 'sqlalchemy', 'tg.devtools']

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
        app = EvalException(app, global_conf,
                            templating_formatters=[],
                            media_paths={},
                            head_html='',
                            footer_html='',
                            libraries=report_libs)
    else:
        app = ErrorMiddleware(app, global_conf, **errorware)

    return app
