import pylons
import inspect
from dispatcher          import ObjectDispatcher
from decoratedcontroller import DecoratedController

class InvalidRequestError(Exception):pass

class RestDispatcher(ObjectDispatcher):
    
    def _handle_post(self, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        method = self._find_first_exposed(current_controller, ['post',])
        if method:
            controller_path.append(method)
            return self, controller_path, remainder

        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)
    
    def _handle_put(self, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        method = self._find_first_exposed(current_controller, ['put'])
        if method:
            controller_path.append(method)
            return self, controller_path, remainder
        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

    def _handle_delete(self, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        method = self._find_first_exposed(current_controller, ['post_delete', 'delete'])
        if method:
            controller_path.append(method)
            return self, controller_path, remainder
        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

    def _handle_get(self, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        if not remainder:
            method = self._find_first_exposed(current_controller, ['get_all', 'get'])
            if method:
                controller_path.append(method)
                return self, controller_path, remainder

        if self._is_exposed(current_controller, 'get_one'):
            method = current_controller.get_one
            args = inspect.getargspec(method)[0]
            fixed_arg_length = args[0]
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
            
        return getattr(self, '_handle_'+method)(url_path, remainder, controller_path)

class RestController(DecoratedController, RestDispatcher):pass