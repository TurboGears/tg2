from inspect import ismethod

import pylons
from pylons.controllers import WSGIController
from tg.exceptions import HTTPNotFound

HTTPNotFound = HTTPNotFound().exception

class Dispatcher(WSGIController):

    def _call(self, controller, params, remainder=None):
        response = controller(*remainder, **dict(params))
        return response

    def __dispatch__(self, url_path, controller_path):
        """override this to define how your controller should dispatch.
        returns: dispatcher, controller_path, url_path
        """
        raise NotImplementedError
    
    def _find_dispatch(self, url_path, controller_path=None):
        """Returns dispatcher, controller_path, remainder"""
        if controller_path is None:
            controller_path = [self,]
        current = controller_path[-1]
        if hasattr(current, '__dispatch__'):
            return current.__dispatch__(url_path, url_path, controller_path)
    
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

        dispatcher, controller_path, remainder = self._find_dispatch(url_path)
        controller = controller_path[-2]
        func = controller_path[-1]
        pylons.c.controller_url = '/'.join(url_path[:-len(remainder)])
        return func, controller, remainder, pylons.request.params.mixed()

    def _perform_call(self, func, args):
        func, controller, remainder, params = self._get_dispatchable(args.get('url'))
        return self._call(func, params, remainder=remainder)
    
    def routes_placeholder(self, url='/', start_response=None, **kwargs):
        """
        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.
        """
        pass

class ObjectDispatcher(Dispatcher):

    def _is_exposed(self, controller, method_name):
        if hasattr(controller, method_name) and ismethod(getattr(controller, method_name)):
            return True

    def _dispatch_first_found_default_or_lookup(self, url_path, remainder, controller_path):
        if len(remainder):
            url_path = url_path[:-len(remainder)]
        for i in xrange(len(controller_path)):
            controller = controller_path[-1]
            if self._is_exposed(controller, 'default'):
                controller_path.append(controller.default)
                return self, controller_path, remainder
#            if self._is_exposed(controller, 'lookup'):
#                controller_path = controller_path[:i+2]
#                controller_path.append(controller.default)
#                return self, controller_path, url_path[-i-1:]
            controller_path.pop()
            if len(url_path):
                remainder.insert(0,url_path[-1])
                url_path.pop()
        raise HTTPNotFound

    def __dispatch__(self, url_path, remainder, controller_path):
        current_controller = controller_path[-1]
        
        #we are plumb out of path, check for index
        if not len(remainder):
            if hasattr(current_controller, 'index'):
                controller_path.append(current_controller.index)
                return  self, controller_path, url_path
            #if there is no index, head up the tree 
            #to see if there is a default or lookup method we can use
            return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)

        current_path = remainder[0]

        #an exposed method matching the path is found
        if self._is_exposed(current_controller, current_path):
            controller_path.append(getattr(current_controller, current_path))
            return self, controller_path, remainder[1:]
        
        #another controller is found and it has a dispatcher object
        if hasattr(current_controller, current_path):
            current_controller = getattr(current_controller, current_path)
            controller_path.append(current_controller)
            if hasattr(current_controller, '__dispatch__'):
                return current_controller.__dispatch__(url_path, remainder[1:], controller_path)
            return self.__dispatch__(url_path, remainder[1:], controller_path)
        
        #dispatch not found
        return self._dispatch_first_found_default_or_lookup(url_path, remainder, controller_path)
