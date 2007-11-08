"""Basic controller class for turbogears"""
from pylons.controllers import ObjectDispatchController, DecoratedController

class TurboGearsController(ObjectDispatchController):
    """Basis TurboGears controller class which is derived from 
    pylons ObjectDispatchController"""
    def _perform_call(self, func, args):
        self._initialize_validation_context()
        controller, remainder, params = self._get_routing_info()
        return DecoratedController._perform_call(self, controller, params, remainder=remainder)
    
    def _dispatch_call(self):
        return self._perform_call(None, None)