from pylons.wsgiapp import PylonsApp

class TGApp(PylonsApp):
    
    def find_controller(self, controller):
        """Locates a controller by attempting to import it then grab
        the SomeController instance from the imported module.
        
        Override this to change how the controller object is found once
        the URL has been resolved.
        
        """
        # Check to see if we've cached the class instance for this name
        if controller in self.controller_classes:
            return self.controller_classes[controller]
        
        # Pull the controllers class name, import controller
        full_module_name = self.config.paths.controller \
            + controller.replace('/', '.')
        
        # Hide the traceback here if the import fails (bad syntax and such)
        __traceback_hide__ = 'before_and_this'
        
        __import__(full_module_name)
        module_name = controller.split('/')[-1]
        class_name = class_name_from_module_name(module_name) + 'Controller'
        if self.log_debug:
            log.debug("Found controller, module: '%s', class: '%s'",
                      full_module_name, class_name)
        self.controller_classes[controller] = mycontroller = \
            getattr(sys.modules[full_module_name], class_name)
        return mycontroller