"""Basic controller class for turbogears"""
import urlparse, urllib
from tg.decorated import ObjectDispatchController, DecoratedController
from pylons import request, response
from tg.exceptions import HTTPFound

class TurboGearsController(ObjectDispatchController):
    """Basis TurboGears controller class which is derived from
    pylons ObjectDispatchController"""
    def _perform_call(self, func, args):
        self._initialize_validation_context()
        routingArgs = None
        if isinstance(args, dict) and 'url' in args:
            routingArgs = args['url']
        controller, remainder, params = self._get_routing_info(routingArgs)
        return DecoratedController._perform_call(self, controller, params, remainder=remainder)

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
    url = urlparse.urljoin(request.path_info, url)
    params.update(kw)
    if params:
        url += (('?' in url) and '&' or '?') + urllib.urlencode(params, True)
    found = HTTPFound(url)
    # Merging cookies and headers from global response into redirect
    for header in response.headerlist:
        if header[0] == 'Set-Cookie' or header[0].startswith('X-'):
            found.headers.append(header)
    raise found

def url(tgpath, tgparams=None, **kw):
    """Broken url() re-implementation from TG1.

    See #1649 for more info.
    """
    from tg import request
    if not isinstance(tgpath, basestring):
        tgpath = "/".join(list(tgpath))
    path = request.relative_url(tgpath)
    print 'path', path
    base_url = request.path_url
    return path[len(base_url):]
