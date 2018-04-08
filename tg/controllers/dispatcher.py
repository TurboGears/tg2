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
import tg
from webob.exc import HTTPException
from tg._compat import unicode_text
from tg.decorators import cached_property
from crank.dispatchstate import DispatchState
from tg.request_local import WebObResponse
import mimetypes as default_mimetypes
import weakref
from ..wsgiapp import TGApp


def dispatched_controller():
    state = tg.request._controller_state
    for location, cont in reversed(state.controller_path):
        if cont.mount_point:
            return cont


class CoreDispatcher(object):
    """Extend this class to define your own mechanism for dispatch."""
    _use_lax_params = True
    _use_index_fallback = False

    def _get_dispatchable(self, context, url_path):
        """
        Returns a :class:`DispatchState` instance.

        :param context: The Request context.
        :param url_path: The url to dispatch.
        """
        req = context.request
        conf = context.config
        
        enable_request_extensions = not conf.get('disable_request_extensions', False)
        dispatch_path_translator = conf.get('dispatch_path_translator', True)

        state = DispatchState(weakref.proxy(req), self, req.args_params, url_path.split('/'),
                              conf.get('ignore_parameters', []),
                              strip_extension=enable_request_extensions,
                              path_translator=dispatch_path_translator)

        if enable_request_extensions:
            try:
                mimetypes = conf['mimetypes']
            except KeyError:
                mimetypes = default_mimetypes

            ext = state.extension
            if ext is not None:
                ext = '.' + ext
                mime_type, encoding = mimetypes.guess_type('file'+ext)
                req._fast_setattr('_response_type', mime_type)
            req._fast_setattr('_response_ext', ext)

        state = state.resolve()

        # Save the dispatch state for possible use within the controller methods
        req._fast_setattr('_controller_state', state)

        if conf.get('enable_routing_args', False):
            state.routing_args.update(state.params)
            if hasattr(state.root_dispatcher, '_setup_wsgiorg_routing_args'):
                state.root_dispatcher._setup_wsgiorg_routing_args(state.path, state.remainder,
                                                                  state.routing_args)

        return state

    def _enter_controller(self, state, remainder):
        if hasattr(state.controller, '_visit'):
            state.controller._visit(*remainder, **state.params)

        return super(CoreDispatcher, self)._enter_controller(state, remainder)

    def _perform_call(self, context):
        """
        This function is called by __call__ to actually perform the controller
        execution.
        """
        py_request = context.request

        state = self._get_dispatchable(context, py_request.quoted_path_info)
        controller, action = state.controller, state.action
        params, remainder = state.params, state.remainder

        if hasattr(controller, '_before'):
            controller._before(*remainder, **params)

        self._setup_wsgi_script_name(state.path, remainder, params)

        r = self._call(action, params, remainder=remainder, context=context)

        if hasattr(controller, '_after'):
            controller._after(*remainder, **params)

        return r

    def __call__(self, environ, context):
        py_response = context.response

        try:
            response = self._perform_call(context)
        except HTTPException as httpe:
            response = httpe

        if response is tg.response or response is py_response:
            # Controller returned the response itself, so we need to do nothing.
            return response

        if response is None:
            # No content
            py_response.body = b''
            if py_response.status_int == 200:
                # Ensure that for missing content we return 'No Content', instead of 200 OK
                py_response.content_type = None
                py_response.status_int = 204
        elif isinstance(response, bytes):
            py_response.body = response
        elif isinstance(response, unicode_text):
            if not py_response.charset:
                py_response.charset = 'utf-8'
            py_response.text = response
        elif isinstance(response, WebObResponse):
            # Copy eventual headers from tg.response
            for name, value in py_response.headers.items():
                header_name = name.lower()
                if header_name in ('content-type', 'content-length'):
                    # Do not overwrite content related headers in returned response
                    continue
                if header_name == 'set-cookie':
                    response.headers.add(name, value)
                else:
                    response.headers.setdefault(name, value)
            py_response = context.response = response
        else:
            py_response.app_iter = response

        return py_response

    @cached_property
    def mount_point(self):
        if not self.mount_steps:
            return ''
        return '/' + '/'.join((x[0] for x in self.mount_steps[1:]))

    @cached_property
    def mount_steps(self):
        def find_url(root, item, parents):
            for i in dir(root):
                if i.startswith('_') or i in ('mount_steps', 'mount_point'):
                    continue

                controller = getattr(root, i)
                if controller is item:
                    return parents + [(i, item)]
                if hasattr(controller, '_dispatch'):
                    v = find_url(controller.__class__,
                        item, parents + [(i, controller)])
                    if v:
                        return v
            return []

        root_controller = tg.config.get('tg.root_controller')
        if root_controller is None:
            root_controller = TGApp.lookup_controller(tg.config, 'root')

        return find_url(root_controller, self, [('/', root_controller)])
