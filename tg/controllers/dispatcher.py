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
from inspect import getargspec, isclass, ismethod

import mimetypes
import sys
from warnings import warn

import pylons
from pylons.controllers import WSGIController

from tg.exceptions import HTTPNotFound
from tg.i18n import setup_i18n
from tg.decorators import cached_property

HTTPNotFound = HTTPNotFound().exception


def dispatched_controller():
    state = pylons.request.controller_state
    for location, cont in reversed(state.controller_path):
        if cont.mount_point:
            return cont
    return None

class DispatchState(object):
    """
    This class keeps around all the pertainent info for the state
    of the dispatch as it traverses through the tree.  This allows
    us to attach things like routing args and to keep track of the
    path the controller takes along the system.
    """
    def __init__(self, url_path, params):
        self.url_path = url_path
        self.controller_path = []
        self.routing_args = {}
        self.method = None
        self.remainder = None
        self.dispatcher = None
        self.params = params
        self._notfound_stack = []

        #remove the ignore params from self.params
        remove_params = pylons.config.get('ignore_parameters', [])
        for param in remove_params:
            if param in self.params:
                del self.params[param]

    def add_controller(self, location, controller):
        """Add a controller object to the stack"""
        self.controller_path.append((location, controller))

    def add_method(self, method, remainder):
        """Add the final method that will be called in the _call method"""
        self.method = method
        self.remainder = remainder

    def add_routing_args(self, current_path, remainder, fixed_args, var_args):
        """
        Add the "intermediate" routing args for a given controller mounted
        at the current_path
        """
        i = 0
        for i, arg in enumerate(fixed_args):
            if i >= len(remainder):
                break
            self.routing_args[arg] = remainder[i]
        remainder = remainder[i:]
        if var_args and remainder:
            self.routing_args[current_path] = remainder

    @property
    def controller(self):
        """returns the current controller"""
        return self.controller_path[-1][1]


class Dispatcher(WSGIController):
    """
       Extend this class to define your own mechanism for dispatch.
    """
    def _call(self, controller, params, remainder=None):
        """Override to define how your controller method should be called."""
        response = controller(*remainder, **dict(params))
        return response

    def _get_argspec(self, func):
        try:
            cached_argspecs = self.__class__._cached_argspecs
        except AttributeError:
            self.__class__._cached_argspecs = cached_argspecs = {}

        try:
            argspec = cached_argspecs[func.im_func]
        except KeyError:
            argspec = cached_argspecs[func.im_func] = getargspec(func)
        return argspec

    def _get_params_with_argspec(self, func, params, remainder):
        params = params.copy()
        argspec = self._get_argspec(func)
        argvars = argspec[0][1:]
        if argvars and enumerate(remainder):
            for i, var in enumerate(argvars):
                if i >= len(remainder):
                    break
                params[var] = remainder[i]
        return params

    def _remove_argspec_params_from_params(self, func, params, remainder):
        """Remove parameters from the argument list that are
           not named parameters
           Returns: params, remainder"""

        # figure out which of the vars in the argspec are required
        argspec = self._get_argspec(func)
        argvars = argspec[0][1:]

        # if there are no required variables, or the remainder is none, we
        # have nothing to do
        if not argvars or not remainder:
            return params, remainder

        # this is a work around for a crappy api choice in getargspec
        argvals = argspec[3]
        if argvals is None:
            argvals = []

        required_vars = argvars
        optional_vars = []
        if argvals:
            required_vars = argvars[:-len(argvals)]
            optional_vars = argvars[-len(argvals):]

        # make a copy of the params so that we don't modify the existing one
        params=params.copy()

        # replace the existing required variables with the values that come in
        # from params these could be the parameters that come off of validation.
        remainder = list(remainder)
        for i, var in enumerate(required_vars):
            if i < len(remainder):
                remainder[i] = params[var]
            elif params.get(var):
                remainder.append(params[var])
            if var in params:
                del params[var]

        #remove the optional positional variables (remainder) from the named parameters
        # until we run out of remainder, that is, avoid creating duplicate parameters
        for i,(original,var) in enumerate(zip(remainder[len(required_vars):],optional_vars)):
            if var in params:
                remainder[ len(required_vars)+i ] = params[var]
                del params[var]

        return params, tuple(remainder)

    def _dispatch(self, state, remainder):
        """override this to define how your controller should dispatch.
        returns: dispatcher, controller_path, remainder
        """
        raise NotImplementedError

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

        state = DispatchState(url_path, params)
        state.add_controller('/', self)
        state.dispatcher = self
        state =  state.controller._dispatch(state, url_path)

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

        if hasattr(controller, '__before__'
                ) and not hasattr(controller, '_before'):
            warn("Support for __before__ is going to removed"
                " in the next minor version, please use _before instead.")
            controller.__before__(*args, **args)

        if hasattr(controller, '_before'):
            controller._before(*args, **args)

        self._setup_wsgi_script_name(url_path, remainder, params)

        r = self._call(func, params, remainder=remainder)

        if hasattr(controller, '__after__'):
            warn("Support for __after__ is going to removed"
                 " in the next minor version,  please use _after instead.")
            controller.__after__(*args, **args)
        if hasattr(controller, '_after'):
            controller._after(*args, **args)
        return r

    def routes_placeholder(self, url='/', start_response=None, **kwargs):
        """Routes placeholder.

        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.

        """
        pass

class ObjectDispatcher(Dispatcher):
    """
    Object dispatch (also "object publishing") means that each portion of the
    URL becomes a lookup on an object.  The next part of the URL applies to the
    next object, until you run out of URL.  Processing starts on a "Root"
    object.

    Thus, /foo/bar/baz become URL portion "foo", "bar", and "baz".  The
    dispatch looks for the "foo" attribute on the Root URL, which returns
    another object.  The "bar" attribute is looked for on the new object, which
    returns another object.  The "baz" attribute is similarly looked for on
    this object.

    Dispatch does not have to be directly on attribute lookup, objects can also
    have other methods to explain how to dispatch from them.  The search ends
    when a decorated controller method is found.

    The rules work as follows:

    1) If the current object under consideration is a decorated controller
       method, the search is ended.

    2) If the current object under consideration has a "_default" method, keep a
       record of that method.  If we fail in our search, and the most recent
       method recorded is a "_default" method, then the search is ended with
       that method returned.

    3) If the current object under consideration has a "_lookup" method, keep a
       record of that method.  If we fail in our search, and the most recent
       method recorded is a "_lookup" method, then execute the "_lookup" method,
       and start the search again on the return value of that method.

    4) If the URL portion exists as an attribute on the object in question,
       start searching again on that attribute.

    5) If we fail our search, try the most recent recorded methods as per 2 and
       3.
    """
    def _find_first_exposed(self, controller, methods):
        for method in methods:
            if self._is_exposed(controller, method):
                return getattr(controller, method)

    def _is_exposed(self, controller, name):
        """Override this function to define how a controller method is
        determined to be exposed.

        :Arguments:
          controller - controller with methods that may or may not be exposed.
          name - name of the method that is tested.

        :Returns:
           True or None
        """
        if ismethod(getattr(controller, name, None)):
            return True

    def _method_matches_args(self, method, state, remainder):
        """
        This method matches the params from the request along with the remainder to the
        method's function signiture.  If the two jive, it returns true.

        It is very likely that this method would go into ObjectDispatch in the future.
        """
        argspec = self._get_argspec(method)
        #skip self,
        argvars = argspec[0][1:]
        argvals = argspec[3]

        required_vars = argvars
        if argvals:
            required_vars = argvars[:-len(argvals)]
        else:
            argvals = []

        #remove the appropriate remainder quotient
        if len(remainder)<len(required_vars):
            #pull the first few off with the remainder
            required_vars = required_vars[len(remainder):]
        else:
            #there is more of a remainder than there is non optional vars
            required_vars = []

        #remove vars found in the params list
        params = state.params
        for var in required_vars[:]:
            if var in params:
                required_vars.pop(0)
            else:
                break;

        var_in_params = 0
        for var in argvars:
            if var in params:
                var_in_params+=1

        #make sure all of the non-optional-vars are there
        if not required_vars:
            var_args = argspec[0][1:]
            #there are more args in the remainder than are available in the argspec
            if len(var_args)<len(remainder) and not argspec[1]:
                return False
            defaults = argspec[3] or []
            var_args = var_args[len(remainder):-len(defaults)]
            for arg in var_args:
                if arg not in state.params:
                    return False
            return True
        return False

    def _is_controller(self, controller, name):
        """
        Override this function to define how an object is determined to be a
        controller.
        """
        return hasattr(controller, name) and not ismethod(getattr(controller, name))

    def _dispatch_controller(self, current_path, controller, state, remainder):
        """
           Essentially, this method defines what to do when we move to the next
           layer in the url chain, if a new controller is needed.
           If the new controller has a _dispatch method, dispatch proceeds to
           the new controller's mechanism.

           Also, this is the place where the controller is checked for
           controller-level security.
        """
        #xxx: add logging?
        if hasattr(controller, '_dispatch'):
            if isclass(controller):
                warn("this functionality is going to removed in the next minor version,"
                     " please create an instance of your sub-controller instead")
                controller = controller()

            obj = getattr(controller, 'im_self', controller)
            if hasattr(obj, '_check_security'):
                obj._check_security()

            state.add_controller(current_path, controller)
            state.dispatcher = controller
            return controller._dispatch(state, remainder)
        state.add_controller(current_path, controller)
        return self._dispatch(state, remainder)

    def _dispatch_first_found_default_or_lookup(self, state, remainder):
        """
        When the dispatch has reached the end of the tree but not found an
        applicable method, so therefore we head back up the branches of the
        tree until we found a method which matches with a _default or _lookup method.
        """

        try:
            m_type, meth, m_remainder, warning = state._notfound_stack.pop()
        except IndexError:
            raise HTTPNotFound
        if warning:
            warn(warning, DeprecationWarning)
        if m_type == 'lookup':
            new_controller, new_remainder = meth(*m_remainder)
            state.add_controller(new_controller.__class__.__name__, new_controller)
            dispatcher = getattr(new_controller, '_dispatch', self._dispatch)
            return dispatcher(state, new_remainder)
        elif m_type == 'default':
            state.add_method(meth, m_remainder)
            state.dispatcher = self
            return state
        else:
            assert False, 'Unknown notfound hander %r' % m_type

    def _dispatch(self, state, remainder):
        """
        This method defines how the object dispatch mechanism works, including
        checking for security along the way.
        """

        current_controller = state.controller
        self._enter_controller(state, remainder)

        #we are plumb out of path, check for index
        if not remainder:
            if hasattr(current_controller, 'index'):
                state.add_method(current_controller.index, remainder)
                return state
            #if there is no index, head up the tree
            #to see if there is a _default or _lookup method we can use
            return self._dispatch_first_found_default_or_lookup(state, remainder)

        current_path = remainder[0]
        current_args = remainder[1:]

        #an exposed method matching the path is found
        if self._is_exposed(current_controller, current_path):
            #check to see if the argspec jives
            controller = getattr(current_controller, current_path)
            if self._method_matches_args(controller, state, current_args):
                state.add_method(controller, current_args)
                return state

        #another controller is found
        if hasattr(current_controller, current_path):
            current_controller = getattr(current_controller, current_path)
            return self._dispatch_controller(
                current_path, current_controller, state, current_args)

        #dispatch not found
        return self._dispatch_first_found_default_or_lookup(state, remainder)

    def _enter_controller(self, state, remainder):
        '''Checks security and pushes any notfound (_lookup or _default) handlers
        onto the stack
        '''

        current_controller = state.controller
        if hasattr(current_controller, '_check_security'):
            current_controller._check_security()
        if self._is_exposed(current_controller, '_lookup'):
            state._notfound_stack.append(('lookup', current_controller._lookup, remainder, None))
        elif self._is_exposed(current_controller, 'lookup'):
            state._notfound_stack.append(('lookup', current_controller.lookup, remainder,
                                          'lookup method is deprecated, please replace with _lookup'))
        if self._is_exposed(current_controller, '_default'):
            state._notfound_stack.append(('default', current_controller._default, remainder, None))
        elif self._is_exposed(current_controller, 'default'):
            state._notfound_stack.append(('default', current_controller.default, remainder,
                                          'default method is deprecated, please replace with _default'))

    def _setup_wsgiorg_routing_args(self, url_path, remainder, params):
        """
        This is expected to be overridden by any subclass that wants to set
        the routing_args (RestController). Do not delete.
        """

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
