from inspect import ismethod, isclass
from warnings import warn
import pylons
import mimetypes
from pylons.controllers import WSGIController
from tg.exceptions import HTTPNotFound

HTTPNotFound = HTTPNotFound().exception

class Dispatcher(WSGIController):

    def _call(self, controller, params, remainder=None):
        """
            Override This function to define how your controller method should be called.
        """
        response = controller(*remainder, **dict(params))
        return response

    def _dispatch(self, url_path, remainder, controller_path):
        """override this to define how your controller should dispatch.
        returns: dispatcher, controller_path, remainder
        """
        raise NotImplementedError
    
    def _find_dispatch(self, url_path, controller_path=None):
        """Returns dispatcher, controller_path, remainder"""
        if controller_path is None:
            controller_path = [self,]
        current = controller_path[-1]
        if hasattr(current, '_dispatch'):
            return current._dispatch(url_path, url_path, controller_path)
    
    def _get_dispatchable(self, url=None):
        """
        Returns a tuple (controller, remainder, params)

        :Parameters:
          url
            url as string
        """
        
        url_path = pylons.request.path.split('/')[1:]

        if url_path[-1] == '':
            url_path.pop()

        if url_path and '.' in url_path[-1]:
            last_remainder = url_path[-1]
            mime_type, encoding = mimetypes.guess_type(last_remainder)
            if mime_type:
                extension_spot = last_remainder.rfind('.')
                extension = last_remainder[extension_spot:]
                url_path[-1] = last_remainder[:extension_spot]
                pylons.request.response_type = mime_type
                pylons.request.response_ext = extension

        dispatcher, controller_path, remainder = self._find_dispatch(url_path)
        controller = controller_path[-2]
        func = controller_path[-1]
        pylons.c.controller_url = '/'.join(url_path[:-len(remainder)])
        return func, controller, remainder, pylons.request.params.mixed()

    def _perform_call(self, func, args):
        func_name = func.__name__
        func, controller, remainder, params = self._get_dispatchable(args.get('url'))

        if hasattr(controller, '__before__'):
            warn("this functionality is going to removed in the next minor version,"\
                 " please use _before instead."
                 )
            controller.__before__(*args)
        if hasattr(controller, '_before'):
            controller._before(*args)
            
        r = self._call(func, params, remainder=remainder)

        if hasattr(controller, '__after__'):
            warn("this functionality is going to removed in the next minor version,"\
                 " please use _after instead."
                 )
            controller.__after__(*args)
        if hasattr(controller, '_after'):
            controller._after(*args)
        return r
    
    def routes_placeholder(self, url='/', start_response=None, **kwargs):
        """
        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.
        """
        pass

class ObjectDispatcher(Dispatcher):

    def _find_first_exposed(self, controller, methods):
        for method in methods:
            if self._is_exposed(controller, method):
                return getattr(controller, method)
    
    def _is_exposed(self, controller, name):
        if hasattr(controller, name) and ismethod(getattr(controller, name)):
            return True
        
    def _is_controller(self, controller, name):
        return hasattr(controller, name) and not ismethod(getattr(controller, name))

    def _dispatch_controller(self, url_path, controller, remainder, controller_path):
        if hasattr(controller, '_dispatch'):
            if isclass(controller):
                warn("this functionality is going to removed in the next minor version,"\
                     " please create an instance of your sub-controller instead"
                     )
                controller = controller()
            if hasattr(controller, "im_self"):
                obj = controller.im_self
            else:
                obj = controller

            if hasattr(obj, '_check_security'):
                obj._check_security()
            controller_path.append(controller)
            return controller._dispatch(url_path, remainder, controller_path)
        if hasattr(controller, '_check_security'):
            controller._check_security()
        controller_path.append(controller)
        return self._dispatch(url_path, remainder, controller_path)
        
    def _dispatch_first_found_default_or_lookup(self, url_path, remainder, controller_path):
        orig_url_path = url_path
        if len(remainder):
            url_path = url_path[:-len(remainder)]
        for i in xrange(len(controller_path)):
            controller = controller_path[-1]
            if self._is_exposed(controller, 'default'):
                controller_path.append(controller.default)
                return self, controller_path, remainder
            if self._is_exposed(controller, 'lookup'):
                controller, remainder = controller.lookup(*remainder)
                return self._dispatch_controller(orig_url_path, controller, remainder[1:], controller_path)
            controller_path.pop()
            if len(url_path):
                remainder.insert(0,url_path[-1])
                url_path.pop()
        raise HTTPNotFound

    def _dispatch(self, url_path, remainder, controller_path):
        current_controller = controller_path[-1]

        #we are plumb out of path, check for index
        if not len(remainder):
            if hasattr(current_controller, 'index'):
                controller_path.append(current_controller.index)
                return  self, controller_path, remainder
            #if there is no index, head up the tree 
            #to see if there is a default or lookup method we can use
            return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

        current_path = remainder[0]

        #an exposed method matching the path is found
        if self._is_exposed(current_controller, current_path):
            controller_path.append(getattr(current_controller, current_path))
            return self, controller_path, remainder[1:]
        
        #another controller is found
        if hasattr(current_controller, current_path):
            current_controller = getattr(current_controller, current_path)
            return self._dispatch_controller(url_path, current_controller, remainder[1:], controller_path)
        
        #dispatch not found
        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)
