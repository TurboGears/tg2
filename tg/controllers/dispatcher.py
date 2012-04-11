"""
This is the main dispatcher module.

Dispatch works as follows:
Start at the RootController, the root controller must
have a _dispatch function, which defines how we move
from object to object in the system.
Continue following the dispatch mechanism for a given
controller until you reach another controller with a
_dispatch method defined.  Use the new _dispatch
method until anther controller with _dispatch defined
or until the url has been traversed to entirety.

This module also contains the standard ObjectDispatch
class which provides the ordinary TurboGears mechanism.

"""

import mimetypes
import sys
from warnings import warn

import pylons
from pylons.controllers import WSGIController

from crank.dispatchstate import DispatchState

from tg.decorators import cached_property
from tg.exceptions import HTTPNotFound
from tg.i18n import setup_i18n


HTTPNotFound = HTTPNotFound().exception


def dispatched_controller():
    state = pylons.request.controller_state
    for location, cont in reversed(state.controller_path):
        if cont.mount_point:
            return cont
    return None


class CoreDispatcher(WSGIController):
    """Extend this class to define your own mechanism for dispatch."""

    _use_lax_params = True
    _use_index_fallback = False

    def _call(self, controller, params, remainder=None):
        """Override to define how your controller method should be called."""
        response = controller(*remainder, **dict(params))
        return response

    def _get_dispatchable(self, url_path):
        """Return a tuple (controller, remainder, params).

        :Parameters:
          url
            url as string

        """
        if not pylons.config.get('disable_request_extensions', False):
            pylons.request.response_type = None
            pylons.request.response_ext = None
            if url_path and '.' in url_path[-1]:
                last_remainder = url_path[-1]
                mime_type, encoding = mimetypes.guess_type(last_remainder)
                if mime_type:
                    extension_spot = last_remainder.rfind('.')
                    extension = last_remainder[extension_spot:]
                    url_path[-1] = last_remainder[:extension_spot]
                    pylons.request.response_type = mime_type
                    pylons.request.response_ext = extension

        params = pylons.request.params.mixed()

        state = DispatchState(pylons.request,
            self, params, url_path, pylons.config.get('ignore_parameters', []))
        state = state.controller._dispatch(state, url_path)

        pylons.tmpl_context.controller_url = '/'.join(
            url_path[:-len(state.remainder)])

        state.routing_args.update(params)
        if hasattr(state.dispatcher, '_setup_wsgiorg_routing_args'):
            state.dispatcher._setup_wsgiorg_routing_args(
                url_path, state.remainder, state.routing_args)

        #save the controller state for possible use within the controller methods
        pylons.request.controller_state = state

        return state.method, state.controller, state.remainder, params

    def _setup_wsgiorg_routing_args(self, url_path, remainder, params):
        """
        This is expected to be overridden by any subclass that wants to set
        the routing_args (RestController). Do not delete.
        """
        # this needs to get added back in after we understand why it breaks pagination:
        # pylons.request.environ['wsgiorg.routing_args'] = (tuple(remainder), params)

    def _setup_wsgi_script_name(self, url_path, remainder, params):
        pass

    def _perform_call(self, func, args):
        """Called from within Pylons and should not be overridden."""
        if pylons.config.get('i18n_enabled', True):
            setup_i18n()

        script_name = pylons.request.environ.get('SCRIPT_NAME', '')
        url_path = pylons.request.path
        if url_path.startswith(script_name):
            url_path = url_path[len(script_name):]
        url_path = url_path.split('/')[1:]

        if url_path[-1] == '':
            url_path.pop()

        func, controller, remainder, params = self._get_dispatchable(url_path)

        if hasattr(controller, '_before'):
            controller._before(*args, **args)

        self._setup_wsgi_script_name(url_path, remainder, params)

        r = self._call(func, params, remainder=remainder)

        if hasattr(controller, '_after'):
            controller._after(*args, **args)
        return r

    def routes_placeholder(self, url='/', start_response=None, **kwargs):
        """Routes placeholder.

        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.

        """
        pass

    @cached_property
    def mount_point(self):
        if not self.mount_steps:
            return ''
        return '/' + '/'.join((x[0] for x in self.mount_steps[1:]))

    @cached_property
    def mount_steps(self):
        def find_url(root, item, parents):
            for i in root.__dict__:
                controller = root.__dict__[i]
                if controller is item:
                    return parents + [(i, item)]
                if hasattr(controller, '_dispatch'):
                    v = find_url(controller.__class__,
                        item, parents + [(i, controller)])
                    if v:
                        return v
            return []

        root_controller = sys.modules[
            pylons.config['application_root_module']].RootController
        return find_url(root_controller, self, [('/', root_controller)])
