"""Decorated Controller"""
import logging

import formencode

import pylons
from pylons.controllers import WSGIController
import tg.exceptions

log = logging.getLogger(__name__)

def _configured_engines():
    """Returns set with the currently configured template engine's names
    from the active application's globals"""
    g = pylons.g._current_obj()
    if not hasattr(g, 'tg_configured_engines'):
        g.tg_configured_engines = set()
    return g.tg_configured_engines


class DecoratedController(WSGIController):

    def _perform_validate(self, controller, params):
        validation = getattr(controller.decoration, 'validation', None)
        if validation is None:
            return params

        if hasattr(validation, '_before_validate'):
            validation._before_validate(controller, params)
        
        new_params=params
        if isinstance(validation.validators, dict):
            errors = {}
            new_params = {}
            for field, validator in validation.validators.iteritems():
                try:
                    new_params[field] = validator.to_python(params.get(field))
                except formencode.api.Invalid, inv:
                    errors[field] = inv

            if errors:
                raise formencode.api.Invalid(
                    formencode.schema.format_compound_error(errors),
                    params, None, error_dict=errors)
        elif isinstance(validation.validators, formencode.Schema):
            new_params = validation.validators.to_python(params)
        elif hasattr(validation.validators, 'validate'):
            new_params = validation.validators.validate(params)


        return new_params

    def _render_response(self, controller, response):
        """Render response takes the dictionary returned by the
        controller calls the appropriate template engine. It uses
        information off of the decoration object to decide which engine
        and template to use, and removes anything in the exclude_names
        list from the returned dictionary.

        The exclude_names functionality allows you to pass variables to
        some template rendering engines, but not others. This behavior
        is particularly useful for rendering engines like JSON or other
        "web service" style engines which don't use and explicit
        template.

        All of these values are populated into the context object by the
        expose decorator.
        """
        content_type, engine_name, template_name, exclude_names = \
            controller.decoration.lookup_template_engine(pylons.request)
        
        # Always set content type
        pylons.response.headers['Content-Type'] = content_type 
        
        req = pylons.request
        
        if template_name is None:
            return response
        
        #Prepare the engine, if it's not already been prepared.
        
        if engine_name not in _configured_engines():
            from pylons import config
            template_options = dict(config).get('buffet.template_options', {})
            pylons.buffet.prepare(engine_name, **template_options)
            _configured_engines().add(engine_name)
        
        # Setup the template namespace, removing anything that the user
        # has marked to be excluded.
        namespace = dict(context=pylons.c)
        namespace.update(response)
        
        for name in exclude_names:
            namespace.pop(name)
        
        # If we are in a test request put the namespace where it can be accessed directly
        if req.environ.get('paste.testing'):
            req.environ['paste.testing_variables']['namespace'] = namespace
            req.environ['paste.testing_variables']['template_name'] = template_name
            req.environ['paste.testing_variables']['exclude_names'] = exclude_names
        
        # Render the result.
        result = pylons.buffet.render(engine_name=engine_name,
                                      template_name=template_name,
                                      include_pylons_variables=False,
                                      namespace=namespace)
        return result

    def _handle_validation_errors(self, controller, exception, args):
        pylons.c.form_errors = exception.error_dict
        pylons.c.form_values = exception.value

        error_handler = controller.decoration.validation.error_handler
        if error_handler is None:
            error_handler = controller
        
        #output = error_handler(controller.im_self, **args2)
#        self._perform_call(error_handler, args2)
        call_params = dict(args)
        for k in call_params.keys():
            # convert unicode keys into str
            # otherwise you get weird TypeError
            if isinstance(k, unicode):
                call_params[str(k)] = call_params.pop(k)
        output = error_handler(controller.im_self, **call_params)
        return error_handler, output

    def _perform_call(self, func, args, remainder=None):
        if remainder is None:
            remainder = []
        try:
            controller, params = func, args
            pylons.request.headers['tg_format'] = params.get('tg_format', None)

            # Validate user input
            controller.decoration.run_hooks('before_validate', remainder,
                                            params)
            params = self._perform_validate(controller, params)
            pylons.c.form_values = params

            # call controller method
            controller.decoration.run_hooks('before_call', remainder, params)
            call_params = dict(params)
            for k in call_params.keys():
                # convert unicode keys into str
                # otherwise you get weird TypeError
                if isinstance(k, unicode):
                    call_params[str(k)] = call_params.pop(k)
            output = controller(*remainder, **call_params)

        except formencode.api.Invalid, inv:
            controller, output = self._handle_validation_errors(controller,
                                                                inv, args)

        # Render template
        controller.decoration.run_hooks('before_render', remainder, params,
                                        output)
        response = self._render_response(controller, output)
        controller.decoration.run_hooks('after_render', response)
        return response

class ObjectDispatchController(DecoratedController):

    def _initialize_validation_context(self):
        pylons.c.form_errors = {}
        pylons.c.form_values = {}

    def _get_routing_info(self, url=None):
        """Returns a tuple (controller, remainder, params)

        :Parameters:
          url
            url as string
        """
        if url is None:
            url_path = pylons.request.path_info.split('/')[1:]
        else:
            url_path = url.split('/')

        controller, remainder = object_dispatch(self, url_path)
        # XXX Place controller url at context temporarily... we should be
        #    really using SCRIPT_NAME for this.
        if remainder:
            pylons.c.controller_url = '/'.join(url_path[:-len(remainder)])
        else:
            pylons.c.controller_url = url
        if remainder and remainder[-1] == '':
            remainder.pop()
        return controller, remainder, pylons.request.params

    def _perform_call(self, func, args):
        self._initialize_validation_context()
        controller, remainder, params = self._get_routing_info(args['url'])
        return DecoratedController._perform_call(self, controller, params,
                                                 remainder=remainder)

    def route(self, url='/', start_response=None, **kwargs):
        pass


def object_dispatch(obj, url_path):
    remainder = url_path
    notfound_handlers = []
    while True:
        try:
            obj, remainder = find_object(obj, remainder, notfound_handlers)
            return obj, remainder
        except tg.exceptions.HTTPException:
            if not notfound_handlers:
                raise
            name, obj, remainder = notfound_handlers.pop()
            if name == 'default':
                return obj, remainder
            else:
                obj, remainder = obj(*remainder)
                continue


def find_object(obj, remainder, notfound_handlers):
    while True:
        if obj is None:
            raise tg.exceptions.HTTPNotFound().exception
        if iscontroller(obj):
            return obj, remainder

        if not remainder or remainder == ['']:
            index = getattr(obj, 'index', None)
            if iscontroller(index):
                return index, remainder

        default = getattr(obj, 'default', None)
        if iscontroller(default):
            notfound_handlers.append(('default', default, remainder))

        lookup = getattr(obj, 'lookup', None)
        if iscontroller(lookup):
            notfound_handlers.append(('lookup', lookup, remainder))

        if not remainder:
            raise tg.exceptions.HTTPNotFound().exception
        obj = getattr(obj, remainder[0], None)
        remainder = remainder[1:]


def iscontroller(obj):
    if not hasattr(obj, '__call__'):
        return False
    if not hasattr(obj, 'decoration'):
        return False
    return obj.decoration.exposed
