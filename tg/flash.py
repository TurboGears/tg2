"""
Flash messaging system for sending info to the user in a non-obtrusive way
"""
import json
import warnings
from tg.request_local import response, request
from tg._compat import unicode_text, url_quote, url_unquote
from tg.configuration.utils import GlobalConfigurable
from tg.support import converters
from markupsafe import escape_silent as escape
from logging import getLogger
from string import Template

log = getLogger(__name__)

DEFAULT_FLASH_TEMPLATE = Template('''\
<div id="${container_id}">
    <div class="${status}">${message}</div>
</div>''')

DEFAULT_JSFLASH_TEMPLATE = Template('''\
<div id="${container_id}"></div>
<script type="text/javascript">
//<![CDATA[
if(!window.webflash){webflash=(function(){var j=document;var k=j.cookie;var f=null;var e=false;\
var g=null;var c=/msie|MSIE/.test(navigator.userAgent);var a=function(m){return j.createTextNode(m.message)};\
var l=function(n,m){};var b=function(o,m){var n=m;if(typeof(o)=="string"){n=window[o]}\
else{if(o){n=o}}return n};var h=function(){var p=k.indexOf(f+"=");if(p<0){return null}\
var o=p+f.length+1;var m=k.indexOf(";",o);if(m==-1){m=k.length}var n=k.substring(o,m);\
j.cookie=f+"=; expires=Fri, 02-Jan-1970 00:00:00 GMT; path=/";return webflash.lj(unescape(n))};\
var i=function(){if(e){return}e=true;var p=h();if(p!==null){var m=j.getElementById(g);\
var n=j.createElement("div");if(p.status){n.setAttribute(c?"className":"class",p.status)}\
var o=a(p);n.appendChild(o);m.style.display="block";if(p.delay){setTimeout(function(){m.style.display="none"},p.delay)}\
m.appendChild(n);l(p,m)}};var d=function(){if(!c){var m="DOMContentLoaded";\
j.addEventListener(m,function(){j.removeEventListener(m,arguments.callee,false);i()},false);\
window.addEventListener("load",i,false)}else{if(c){var m="onreadystatechange";\
j.attachEvent(m,function(){j.detachEvent(m,arguments.callee);i()});\
if(j.documentElement.doScroll&&!frameElement){(function(){if(e){return}try{j.documentElement.doScroll("left")}\
catch(n){setTimeout(arguments.callee,0);return}i()})()}window.attachEvent("load",i)}}};\
return function(m){f=m.name||"webflash";g=m.id||"webflash";l=b(m.on_display,l);a=b(m.create_node,a);\
return{payload:h,render:d}}})();webflash.lj=function(s){var r;eval("r="+s);return r}};
(function() {
var webflash = window.webflash({"id": "${container_id}", "name": "${cookie_name}"});
${js_call}
})()
//]]>
</script>''')


class TGFlash(GlobalConfigurable):
    """Support for flash messages stored in a plain cookie.

    Supports both fetching flash messages on server side and on client side
    through Javascript.

    When used from Python itself, the flash object provides a :meth:`.TGFlash.render`
    method that can be used from templates to render the flash message.

    When used on Javascript, calling the :meth:`.TGFlash.render` provides a ``webflash``
    javascript object which exposes ``.payload()`` and ``.render()`` methods that can
    be used to get current message and render it from javascript.

    For a complete list of options supported by Flash objects see :meth:`.TGFlash.configure`.
    """

    CONFIG_NAMESPACE = 'flash.'
    CONFIG_OPTIONS = {'template': converters.astemplate,
                      'js_template': converters.astemplate,
                      'allow_html': converters.asbool}

    def __init__(self, **options):
        self.configure(**options)

    def configure(self, cookie_name="webflash", default_status="ok",
                  template=DEFAULT_FLASH_TEMPLATE,
                  js_call='webflash.render()',
                  js_template=DEFAULT_JSFLASH_TEMPLATE,
                  allow_html=False):
        """Flash messages can be configured through :class:`.AppConfig` (``app_cfg.base_config``)
        using the following options:

        - ``flash.cookie_name`` -> Name of the cookie used to store flash messages
        - ``flash.default_status`` -> Default message status if not specified (``ok`` by default)
        - ``flash.template`` -> :class:`string.Template` instance used as the flash template when
          rendered from server side, will receive ``$container_id``, ``$message`` and ``$status``
          variables.
        - ``flash.allow_html`` -> Turns on/off escaping in flash messages, by default HTML is not allowed.
        - ``flash.js_call`` -> javascript code which will be run when displaying the flash
          from javascript. Default is ``webflash.render()``, you can use ``webflash.payload()``
          to retrieve the message and show it with your favourite library.
        - ``flash.js_template`` -> :class:`string.Template` instance used to replace full
          javascript support for flash messages. When rendering flash message for javascript usage
          the following code will be used instead of providing the standard ``webflash`` object.
          If you replace ``js_template`` you must also ensure cookie parsing and delete it for
          already displayed messages. The template will receive: ``$container_id``,
          ``$cookie_name``, ``$js_call`` variables.

        """
        self.default_status = default_status
        self.cookie_name = cookie_name
        self.static_template = template
        self.js_call = js_call
        self.js_template = js_template
        self.allow_html = allow_html

    def __call__(self, message, status=None, **extra_payload):
        """Registers a flash message for display on current or next request."""
        # Force the message to be unicode so lazystrings, etc... are coerced
        message = unicode_text(message)

        payload = self._prepare_payload(message=message,
                                        status=status or self.default_status,
                                        **extra_payload)

        if request is not None:
            # Save the payload in environ too in case JavaScript is not being
            # used and the message is being displayed in the same request.
            request.environ['webflash.payload'] = payload

        resp = response._current_obj()
        resp.set_cookie(self.cookie_name, payload)
        if len(resp.headers['Set-Cookie']) > 4096:
            raise ValueError('Flash value is too long (cookie would be >4k)')

    def _prepare_payload(self, **data):
        return url_quote(json.dumps(data))

    def _get_message(self, payload):
        msg = payload.get('message','')
        if self.allow_html is False:
            msg = escape(msg)
        return msg

    def render(self, container_id, use_js=True):
        """Render the flash message inside template or provide Javascript support for them.

        ``container_id`` is the DIV where the messages will be displayed, while ``use_js``
        switches between rendering the flash as HTML or for Javascript usage.

        """
        if use_js:
            return self._render_js_version(container_id)
        else:
            return self._render_static_version(container_id)

    def _render_static_version(self, container_id):
        payload = self.pop_payload()
        if not payload:
            return ''
        payload['message'] = self._get_message(payload)
        payload['container_id'] = container_id
        return self.static_template.substitute(payload)

    def _render_js_version(self, container_id):
        return self.js_template.substitute(container_id=container_id,
                                           cookie_name=self.cookie_name,
                                           js_call=self.js_call)

    def pop_payload(self):
        """Fetch current flash message, status and related information.

        Fetching flash message deletes the associated cookie.
        """
        # First try fetching it from the request
        req = request._current_obj()
        payload = req.environ.get('webflash.payload', {})
        if not payload:
            payload = req.cookies.get(self.cookie_name, {})

        if payload:
            payload = json.loads(url_unquote(payload))
            if 'webflash.deleted_cookie' not in req.environ:
                response.delete_cookie(self.cookie_name)
                req.environ['webflash.delete_cookie'] = True
        return payload or {}

    @property
    def message(self):
        """Get only current flash message, getting the flash message will delete the cookie."""
        return self.pop_payload().get('message')

    @property
    def status(self):
        """Get only current flash status, getting the flash status will delete the cookie."""
        return self.pop_payload().get('status') or self.default_status


flash = TGFlash.create_global()


def get_flash():
    warnings.warn("get_flash() is deprecated, use tg.flash.message instead",
                  DeprecationWarning, stacklevel=2)
    return flash.message


def get_status():
    warnings.warn("get_status() is deprecated, use tg.flash.status instead",
                  DeprecationWarning, stacklevel=2)
    return flash.status
