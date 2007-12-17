"""Basic controller class for turbogears"""
from pylons.controllers import ObjectDispatchController, DecoratedController
from pylons import response
from tg.exceptions import HTTPFound

class TurboGearsController(ObjectDispatchController):
    """Basis TurboGears controller class which is derived from
    pylons ObjectDispatchController"""
    def _perform_call(self, func, args):
        self._initialize_validation_context()
        controller, remainder, params = self._get_routing_info()
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
