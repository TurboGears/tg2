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
from warnings import warn
import tg, sys
import mimetypes
from webob.exc import HTTPException
from tg._compat import unicode_text
from tg.exceptions import HTTPNotFound
from tg.i18n import setup_i18n
from tg.decorators import cached_property
from crank.dispatchstate import DispatchState

def dispatched_controller():
    state = tg.request._controller_state
    for location, cont in reversed(state.controller_path):
        if cont.mount_point:
            return cont

class CoreDispatcher(object):
    """Extend this class to define your own mechanism for dispatch."""
    _use_lax_params = True
    _use_index_fallback = False

    def _get_dispatchable(self, thread_locals, url_path):
        """
        Returns a tuple (controller, remainder, params)

        :Parameters:
          url
            url as string
        """
        req = thread_locals.request
        conf = thread_locals.config

        params = req.args_params
        state = DispatchState(req, self, params, url_path, conf.get('ignore_parameters', []))

        if not conf.get('disable_request_extensions', False):
            ext = state.extension
            if ext is not None:
                ext = '.' + ext
                mime_type, encoding = mimetypes.guess_type('file'+ext)
                req._fast_setattr('_response_type', mime_type)
            req._fast_setattr('_response_ext', ext)

        state =  state.controller._dispatch(state, url_path)
        thread_locals.tmpl_context.controller_url = '/'.join(url_path[:-len(state.remainder)])

        if conf.get('enable_routing_args', False):
            state.routing_args.update(params)
            if hasattr(state.dispatcher, '_setup_wsgiorg_routing_args'):
                state.dispatcher._setup_wsgiorg_routing_args(url_path, state.remainder, state.routing_args)

        #save the controller state for possible use within the controller methods
        req._fast_setattr('_controller_state', state)

        return state.method, state.controller, state.remainder, params

    def _perform_call(self, thread_locals):
        """
        This function is called from within Pylons and should not be overidden.
        """
        py_request = thread_locals.request
        py_config = thread_locals.config

        if py_config.get('i18n_enabled', True):
            setup_i18n(thread_locals)

        url_path = py_request.path.split('/')[1:]
        if url_path[-1] == '':
            url_path.pop()

        func, controller, remainder, params = self._get_dispatchable(thread_locals, url_path)

        if hasattr(controller, '_before'):
            controller._before(*remainder, **params)

        self._setup_wsgi_script_name(url_path, remainder, params)

        r = self._call(func, params, remainder=remainder, tgl=thread_locals)

        if hasattr(controller, '_after'):
            controller._after(*remainder, **params)

        return r

    def routes_placeholder(self, url='/', start_response=None, **kwargs): #pragma: no cover
        """Routes placeholder.

        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.
        """
        pass

    def __call__(self, environ, start_response):
        thread_locals = environ['tg.locals']
        py_response = thread_locals.response
        py_request = thread_locals.request

        #Replace start_response and track if it is called
        #this is to track if the controller is passing control to a plain
        #WSGI application instead of a TG controller.
        start_response_called = []
        def repl_start_response(status, headers, exc_info=None):
            start_response_called.append(None)
            headers.extend(header for header in environ['tg.locals'].response.headerlist
            if header[0] == 'Set-Cookie' or
               header[0].startswith('X-'))
            return start_response(status, headers, exc_info)
        py_request._fast_setattr('start_response', repl_start_response)

        try:
            response = self._perform_call(thread_locals)
        except HTTPException as httpe:
            response = httpe

        #If we reached a plain WSGI application do not build the response
        #but simply pass the response as is.
        if not start_response_called:
            py_request._fast_setattr('start_response', start_response)
            if isinstance(response, bytes):
                py_response.body = response
            elif isinstance(response, unicode_text):
                if not py_response.charset:
                    py_response.charset = 'utf-8'
                py_response.text = response
            elif hasattr(response, 'wsgi_response'):
                for name, value in py_response.headers.items():
                    if name.lower() == 'set-cookie':
                        response.headers.add(name, value)
                    else:
                        response.headers.setdefault(name, value)
                thread_locals.response = response
                py_response = response
            elif response is None:
                pass
            else:
                py_response.app_iter = response
            response = py_response

        if hasattr(response, 'wsgi_response'):
            if 'paste.testing_variables' in environ:
                # Copy the response object into the testing vars if we're testing
                environ['paste.testing_variables']['response'] = response
            return response(environ, start_response)

        return response

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

        if 'tg.root_controller' in tg.config:
            root_controller = tg.config['tg.root_controller']
        else:
            root_controller = sys.modules[tg.config['application_root_module']].RootController
        return find_url(root_controller, self, [('/', root_controller)])
