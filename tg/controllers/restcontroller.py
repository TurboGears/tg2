import pylons
from pylons.controllers.util import abort
import inspect
from dispatcher          import ObjectDispatcher
from decoratedcontroller import DecoratedController

class InvalidRequestError(Exception):pass

class RestDispatcher(ObjectDispatcher):
    def _handle_put_or_post(self, method, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        if remainder:
            if self._is_exposed(current_controller, remainder[0]):
                controller_path.append(getattr(current_controller, remainder[0]))
                return self, controller_path, remainder[1:]

            if self._is_controller(current_controller, remainder[0]):
                current_controller = getattr(current_controller, remainder[0])
                return self._dispatch_controller(url_path, current_controller, remainder[1:], controller_path)

            r = self._check_for_sub_controllers(url_path, remainder, controller_path)
            if r:
                return r
            
        method = self._find_first_exposed(current_controller, [method,])
        if method:
            args = inspect.getargspec(method)
            fixed_arg_length = len(args[0])-1
            var_args = args[1]
            if fixed_arg_length == len(remainder) or var_args:
                controller_path.append(method)
                return self, controller_path, remainder

        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

    def _handle_delete(self, method, url_path, remainder, controller_path):
        r = self._check_for_sub_controllers(url_path, remainder, controller_path)
        if r:
            return r

        current_controller = controller_path[-1]
        method = self._find_first_exposed(current_controller, ('post_delete', 'delete'))
        if method:
            args = inspect.getargspec(method)
            fixed_arg_length = len(args[0])-1
            var_args = args[1]
            if fixed_arg_length == len(remainder) or var_args:
                controller_path.append(method)
                return self, controller_path, remainder

        #you may not send a delete request to a non-delete function
        if remainder and self._is_exposed(current_controller, remainder[0]):
            abort(405)


        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)
    
    def _check_for_sub_controllers(self, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        method = None
        for find in ('get_one', 'get'):
            if hasattr(current_controller, find):
                method = find
                break
        if method is None:
            return
        args = inspect.getargspec(getattr(current_controller, method))
        fixed_arg_length = len(args[0])-1
        var_args = args[1]
        if var_args:
            for i, item in enumerate(remainder):
                if hasattr(current_controller, item) and self._is_controller(current_controller, item):
                    current_controller = getattr(current_controller, item)
                    return self._dispatch_controller(url_path, current_controller, remainder[i+1:], controller_path)
        elif fixed_arg_length< len(remainder) and hasattr(current_controller, remainder[fixed_arg_length]):
            item = remainder[fixed_arg_length]
            if hasattr(current_controller, item):
                if self._is_controller(current_controller, item):
                    current_controller = getattr(current_controller, item)
                    controller_path.append(current_controller)
                    return self._dispatch_controller(url_path, current_controller, remainder[fixed_arg_length+1:], controller_path)

    def _handle_delete_edit_or_new(self, url_path, remainder, controller_path):
        method = remainder[-1]
        if method not in ('new', 'edit', 'delete'):
            return
        if method == 'delete':
            method = 'get_delete'

        current_controller = controller_path[-1]
        r = self._check_for_sub_controllers(url_path, remainder, controller_path)
        if r:
            return r

        if self._is_exposed(current_controller, method):
            method = getattr(current_controller, method)
            args = inspect.getargspec(method)
            fixed_arg_length = len(args[0])-1
            var_args = args[1]
            if fixed_arg_length == len(remainder) -1 or var_args:
                current_controller = method
                controller_path.append(current_controller)
                return self, controller_path, remainder[:-1]

    def _handle_get(self, method, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        if not remainder:
            method = self._find_first_exposed(current_controller, ('get_all', 'get'))
            if method:
                controller_path.append(method)
                return self, controller_path, remainder
            return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

        #test for "edit" or "new"
        r = self._handle_delete_edit_or_new(url_path, remainder, controller_path)
        if r: 
            return r
        
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

            if len(remainder) == fixed_arg_length:
                controller_path.append(method)
                return self, controller_path, remainder
                
            r = self._check_for_sub_controllers(url_path, remainder, controller_path)
            if r:
                return r

        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)
    
    _handler_lookup = {
        'put':_handle_put_or_post,
        'post':_handle_put_or_post,
        'delete':_handle_delete,
        'get':_handle_get,
        }

    def _dispatch(self, url_path, remainder, controller_path):
        """returns: dispatcher, controller_path, remainder
        """
        method = pylons.request.method.lower()
        
        #conventional hack for handling methods which are not supported by most browsers
        request_method = pylons.request.params.get('_method', None)
        if request_method:
            request_method = request_method.lower()
            #make certain that DELETE and PUT requests are not sent with GET
            if method == 'get' and request_method == 'put':
                abort(405)
            if method == 'get' and request_method == 'delete':
                abort(405)
            method = request_method
           
        r = self._handler_lookup[method](self, method, url_path, remainder, controller_path)
        
        #clear out the method hack
        if '_method' in pylons.request.POST:
            del pylons.request.POST['_method']
        if '_method' in pylons.request.GET:
            del pylons.request.GET['_method']

        return r

class RestController(DecoratedController, RestDispatcher):pass