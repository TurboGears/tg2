"""Basic controller class for turbogears"""

import logging

import urlparse, urllib
from tg.decorated import ObjectDispatchController, DecoratedController
from tg.exceptions import HTTPFound, HTTPException
import pylons

log = logging.getLogger(__name__)

class TurboGearsController(ObjectDispatchController):
    """Basis TurboGears controller class which is derived from
    pylons ObjectDispatchController"""

    def _setup_i18n(self):
        from pylons.i18n import add_fallback, set_lang, LanguageError
        languages = pylons.request.accept_language.best_matches()
        if languages:
            for lang in languages[:]:
                try:
                    add_fallback(lang)
                except LanguageError:
                    # if there is no resource bundle for this language
                    # remove the language from the list
                    languages.remove(lang)
                    log.debug("Skip language %s: not supported", lang)
            # if any language is left, set the best match as a default
            if languages:
                set_lang(languages[0])
                log.info("Set request language to %s", languages[0])

    def _perform_call(self, func, args):
        self._setup_i18n()
        self._initialize_validation_context()
        routingArgs = None
        if isinstance(args, dict) and 'url' in args:
            routingArgs = args['url']
        try:
            controller, remainder, params = self._get_routing_info(routingArgs)
            result = DecoratedController._perform_call(
                self, controller, params, remainder=remainder
                )
        except HTTPException, httpe:
            result = httpe
            # 304 Not Modified's shouldn't have a content-type set
            if result.status_int == 304:
                result.headers.pop('Content-Type', None)
            result._exception = True
        return result

    def _dispatch_call(self):
        return self._perform_call(None, None)

def redirect(url, params=None, **kw):
    """Generate an HTTP redirect. The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the second
    request.
    """
    if not params:
        params = {}

    url = urlparse.urljoin(pylons.request.url, url)
    params.update(kw)
    if params:
        url += (('?' in url) and '&' or '?') + urllib.urlencode(params, True)
    if isinstance(url, unicode):
        url = url.encode('utf8')
    found = HTTPFound(location=url).exception
    
    #TODO: Make this work with WebOb
    
    ## Merging cookies and headers from global response into redirect
    #for header in pylons.response.headerlist:
        #if header[0] == 'Set-Cookie' or header[0].startswith('X-'):
            #found.headers.append(header)
    raise found

def url(tgpath, tgparams=None, **kw):
    """Broken url() re-implementation from TG1.
    See #1649 for more info.
    """

    if not isinstance(tgpath, basestring):
        tgpath = "/".join(list(tgpath))
    if tgpath.startswith("/"):
        app_root = pylons.request.application_url[len(pylons.request.host_url):]
        tgpath = app_root + tgpath
        tgpath = pylons.config.get("server.webpath", "") + tgpath 
        result = tgpath
    else:
        result = tgpath 

    if tgparams is None:
        tgparams = kw
    else:
        try:
            tgparams = tgparams.copy()
            tgparams.update(kw)
        except AttributeError:
            raise TypeError('url() expects a dictionary for query parameters')

    args = []
    for key, value in tgparams.iteritems():
        if value is None:
            continue

        if isinstance(value, (list, tuple)):
            pairs = [(key, v) for v in value]
        else:
            pairs = [(key, value)]
        
        for (k, v) in pairs:
            if v is None:
                continue

            if isinstance(v, unicode):
                v = v.encode("utf8")

            args.append("%s=%s" % (k, urllib.quote(str(v))))

    if args:
        result += "?" + "&".join(args)

    return result

