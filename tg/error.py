import pylons
from paste.deploy.converters import asbool
from pylons.error import template_error_formatters
from weberror.evalexception import EvalException
from weberror.errormiddleware import ErrorMiddleware

media_path = pylons.middleware.media_path
report_libs = pylons.middleware.report_libs
if 'tg.devtools' not in report_libs:
    report_libs.extend(['tg.devtools'])
header_html = pylons.middleware.head_html

footer_html = """\
<script src="{{prefix}}/media/pylons/javascripts/traceback.js"></script>
<script>
var TRACEBACK = {
    uri: "{{prefix}}",
    host: "%s",
    traceback: "/tracebacks"
}
</script>
<div id="service_widget">
<h2 class="assistance">TurboGears Online Assistance</h2>
<div id="nv">
<ul id="supportnav">
    <li class="nav active"><a class="overview" href="#">Overview</a></li>
    <li class="nav"><a class="search" href="#">Search Mail Lists</a></li>
    <li class="nav"><a class="posttraceback" href="#">Post Traceback</a></li>
</ul>
</div>
<div class="clearfix">&nbsp;</div>
<div class="overviewtab">
<h3>Looking for help?</h3>

<p>Here are a few tips for troubleshooting if the above traceback isn't
helping out.</p>

<ol>
<li>Search the mail list</li>
<li>Post the traceback, and ask for help on IRC</li>
<li>Post a message to the mail list, referring to the posted traceback</li>

</div>
<div class="posttracebacktab">
<p><b>Note:</b> Clicking this button will post your traceback to the PylonsHQ website.
The traceback includes the module names, Python version, and lines of code that you
can see above. All tracebacks are posted anonymously unless you're logged into the
PylonsHQ website in this browser.</p>
<input type="button" href="#" class="submit_traceback" value="Send TraceBack to PylonsHQ" style="text-align: center;"/>
</div>

<div class="searchtab">
<p>The following mail lists will be searched:<br />
<input type="checkbox" name="lists" value="python" /> Python<br />
<input type="checkbox" name="lists" value="pylons" checked="checked" /> Pylons<br />
<input type="checkbox" name="lists" value="turbogears" checked="checked" /> TurboGears<br />
<input type="checkbox" name="lists" value="sqlalchemy" /> SQLAlchemy<br />
<input type="checkbox" name="lists" value="genshi" /> Genshi<br />
<input type="checkbox" name="lists" value="toscawidgets" /> ToscaWidgets<br />
<input type="checkbox" name="lists" value="mako" /> Mako<br />
<input type="checkbox" name="lists" value="sqlalchemy" /> SQLAlchemy</p>
<p class="query">for: <input type="text" name="query" class="query" /></p>

<p><input type="submit" value="Search" /></p>
<div class="searchresults">

</div>
</div>

</div>
<div id="pylons_logo">\
<img src="{{prefix}}/media/pylons/img/pylons-tower120.png" /></div>
<div class="credits">Pylons version %s</div>"""

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
        footer = footer_html % (pylons.configuration.config.get('traceback_host', 
                                                  'pylonshq.com'),
                                pylons.__version__)
                                
        py_media = dict(pylons=media_path)
        
        app = EvalException(app, global_conf, 
                            templating_formatters=template_error_formatters,
                            media_paths=py_media, head_html=header_html, 
                            footer_html=footer,
                            libraries=report_libs)
    else:
        app = ErrorMiddleware(app, global_conf, **errorware)
    return app
