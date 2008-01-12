"""Basic controller class for turbogears"""
from pylons.controllers import ObjectDispatchController, DecoratedController
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

def redirect(url, redirect_params=None, **kw):
    """Redirect to a given url."""
    params = redirect_params or {}
    params.update(kw)
    if params:
        url += '?' + urllib.urlencode(params, True)
    found = HTTPFound(url)
    # Merging cookies in global response into redirect
    for c in response.cookies.values():
        found.headers.append(('Set-Cookie', c.output(header='')))
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
