import pylons
from pylons.controllers.util import abort
import inspect
from dispatcher          import ObjectDispatcher
from decoratedcontroller import DecoratedController

class InvalidRequestError(Exception):pass

class RestDispatcher(ObjectDispatcher):
    def _handle_put_or_post(self, method, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        if not remainder:
            method = self._find_first_exposed(current_controller, [method,])
            if method:
                args = inspect.getargspec(method)
                fixed_arg_length = len(args[0])-1
                var_args = args[1]
                if fixed_arg_length == len(remainder) or var_args:
                    controller_path.append(method)
                    return self, controller_path, remainder
                return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

        if self._is_exposed(current_controller, remainder[0]):
            controller_path.append(getattr(current_controller, remainder[0]))
            return self, controller_path, remainder[1:]

        if self._is_controller(current_controller, remainder[0]):
            current_controller = getattr(current_controller, remainder[0])
            return self._dispatch_controller(url_path, current_controller, remainder[1:], controller_path)

        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

    def _handle_delete(self, method, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        method = self._find_first_exposed(current_controller, ['post_delete', 'delete'])
        if method:
            args = inspect.getargspec(method)
            fixed_arg_length = len(args[0])-1
            var_args = args[1]
            if fixed_arg_length == len(remainder) or var_args:
                controller_path.append(method)
                return self, controller_path, remainder

        if self._is_exposed(current_controller, remainder[0]):
            abort(405)

        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

    def _handle_get(self, method, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        if not remainder:
            method = self._find_first_exposed(current_controller, ['get_all', 'get'])
            if method:
                controller_path.append(method)
                return self, controller_path, remainder
            return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

        if self._is_exposed(current_controller, remainder[0]):
            controller_path.append(getattr(current_controller, remainder[0]))
            return self, controller_path, remainder[1:]
        
        if self._is_controller(current_controller, remainder[0]):
            current_controller = getattr(current_controller, remainder[0])
            return self._dispatch_controller(url_path, current_controller, remainder[1:], controller_path)
        
        if self._is_exposed(current_controller, 'get_one'):
            method = current_controller.get_one
            args = inspect.getargspec(method)
            fixed_arg_length = len(args[0])-1
            var_args = args[1]

            if remainder[-1] == 'delete' and self._is_exposed(current_controller, 'get_delete'):
                remainder = remainder[:-1]
                if len(remainder) == fixed_arg_length or var_args:
                    controller_path.append(current_controller.get_delete)
                    return self, controller_path, remainder
            
            if len(remainder) == fixed_arg_length or var_args:
                controller_path.append(method)
                return self, controller_path, remainder

        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)
    
    _handler_lookup = {
        'put':_handle_put_or_post,
        'post':_handle_put_or_post,
        'delete':_handle_delete,
        'get':_handle_get,
        }

    def __dispatch__(self, url_path, remainder, controller_path):
        """returns: dispatcher, controller_path, remainder
        """

        request_method = method = pylons.request.method.lower()

        #conventional hack for handling methods which are not supported by most browsers
        params = pylons.request.params
        if '_method' in params:
            if params['_method']:
                method = params['_method'].lower()
                if request_method == 'get' and method == 'put':
                    raise InvalidRequestError('You may not use GET to perform a PUT request')
                if request_method == 'get' and method == 'delete':
                    raise InvalidRequestError('You may not use GET to perform a DELETE request')
                if '_method' in pylons.request.POST:
                    del pylons.request.POST['_method']
                if '_method' in pylons.request.GET:
                    del pylons.request.GET['_method']
        
        return self._handler_lookup[method](self, method, url_path, remainder, controller_path)

class RestController(DecoratedController, RestDispatcher):pass