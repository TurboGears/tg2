# -*- coding: utf-8 -*-
"""
This module defines the class for decorating controller methods so that on
call the methods can be expressed using expose, validate, and other
decorators to effect a rendered page.
"""

import inspect, operator
import tg
from tg.controllers.util import abort
from tg.predicates import NotAuthorizedError, not_anonymous

from crank.util import (get_params_with_argspec,
                        remove_argspec_params_from_params)

from tg.flash import flash
from tg.jsonify import JsonEncodeError
from tg.render import render as tg_render
from tg.controllers.util import pylons_formencode_gettext
from tg.util import call_controller
from tg.validation import (_navigate_tw2form_children, _FormEncodeSchema,
                           _Tw2ValidationError, validation_errors,
                           _FormEncodeValidator, TGValidationError)

from tg._compat import unicode_text, with_metaclass, im_self, url2pathname

strip_string = operator.methodcaller('strip')

class _DecoratedControllerMeta(type):
    def __init__(cls, name, bases, attrs):
        super(_DecoratedControllerMeta, cls).__init__(name, bases, attrs)
        for name, value in attrs.items():
            #Inherit decorations for methods exposed with inherit=True
            if hasattr(value, 'decoration') and value.decoration.inherit:
                for pcls in reversed(bases):
                    parent_method = getattr(pcls, name, None)
                    if parent_method and hasattr(parent_method, 'decoration'):
                        value.decoration.merge(parent_method.decoration)

class DecoratedController(with_metaclass(_DecoratedControllerMeta, object)):
    """Decorated controller object.

    Creates an interface to hang decoration attributes on
    controller methods for the purpose of rendering web content.

    """
    def _is_exposed(self, controller, name):
        method = getattr(controller, name, None)
        if method and inspect.ismethod(method) and hasattr(method, 'decoration'):
            return method.decoration.exposed

    def _call(self, controller, params, remainder=None, tgl=None):
        """Run the controller with the given parameters.

        _call is called by _perform_call in CoreDispatcher.

        Any of the before_validate hook, the validation, the before_call hook,
        and the controller method can return a FormEncode Invalid exception,
        which will give the validation error handler the opportunity to provide
        a replacement decorated controller method and output that will
        subsequently be rendered.

        This allows for validation to display the original page or an
        abbreviated form with validation errors shown on validation failure.

        The before_render hook provides a place for functions that are called
        before the template is rendered. For example, you could use it to
        add and remove from the dictionary returned by the controller method,
        before it is passed to rendering.

        The after_render hook can act upon and modify the response out of
        rendering.

        """
        if tgl is None: #pragma: no cover
            #compatibility with old code that didn't pass request locals explicitly
            tgl = tg.request.environ['tg.locals']

        self._initialize_validation_context(tgl)

        #This is necessary to prevent spurious Content Type header which would
        #cause problems to paste.response.replace_header calls and cause
        #responses wihout content type to get out with a wrong content type
        resp_headers = tgl.response.headers
        if not resp_headers.get('Content-Type'):
            resp_headers.pop('Content-Type', None)

        if remainder:
            remainder = tuple(map(url2pathname, remainder or []))
        else:
            remainder = tuple()

        tg_decoration = controller.decoration
        try:
            tg_decoration.run_hooks(tgl, 'before_validate', remainder, params)

            validate_params = get_params_with_argspec(controller, params, remainder)

            # Validate user input
            params = self._perform_validate(controller, validate_params)

            tgl.tmpl_context.form_values = params

            tg_decoration.run_hooks(tgl, 'before_call', remainder, params)

            params, remainder = remove_argspec_params_from_params(controller, params, remainder)

            #apply controller wrappers
            try:
                controller_caller = tgl.config['controller_caller']
            except KeyError:
                controller_caller = call_controller

            # call controller method
            output = controller_caller(controller, remainder, params)

        except validation_errors as inv:
            controller, output = self._handle_validation_errors(controller, remainder, params, inv)

        #Be sure that we run hooks if the controller changed due to validation errors
        tg_decoration = controller.decoration

        # Render template
        tg_decoration.run_hooks(tgl, 'before_render', remainder, params, output)

        response = self._render_response(tgl, controller, output)
        
        tg_decoration.run_hooks(tgl, 'after_render', response)
        
        return response['response']

    def _perform_validate(self, controller, params):
        """Run validation for the controller with the given parameters.

        Validation is stored on the "validation" attribute of the controller's
        decoration.

        If can be in three forms:

        1) A dictionary, with key being the request parameter name, and value a
           FormEncode validator.

        2) A FormEncode Schema object

        3) Any object with a "validate" method that takes a dictionary of the
           request variables.

        Validation can "clean" or otherwise modify the parameters that were
        passed in, not just raise an exception.  Validation exceptions should
        be FormEncode Invalid objects.

        """

        validation = getattr(controller.decoration, 'validation', None)

        if validation is None:
            return params

        # An object used by FormEncode to get translator function
        formencode_state = type('state', (), {'_': staticmethod(pylons_formencode_gettext)})

        #Initialize new_params -- if it never gets updated just return params
        new_params = {}

        # The validator may be a dictionary, a FormEncode Schema object, or any
        # object with a "validate" method.
        if isinstance(validation.validators, dict):
            # TG developers can pass in a dict of param names and FormEncode
            # validators.  They are applied one by one and builds up a new set
            # of validated params.

            errors = {}
            for field, validator in validation.validators.items():
                try:
                    if isinstance(validator, _FormEncodeValidator):
                        new_params[field] = validator.to_python(params.get(field),
                                                                formencode_state)
                    else:
                        new_params[field] = validator.to_python(params.get(field))
                # catch individual validation errors into the errors dictionary
                except validation_errors as inv:
                    errors[field] = inv

            # Parameters that don't have validators are returned verbatim
            for param, param_value in params.items():
                if not param in new_params:
                    new_params[param] = param_value

            # If there are errors, create a compound validation error based on
            # the errors dictionary, and raise it as an exception
            if errors:
                raise TGValidationError(TGValidationError.make_compound_message(errors),
                                        value=params,
                                        error_dict=errors)

        elif isinstance(validation.validators, _FormEncodeSchema):
            # A FormEncode Schema object - to_python converts the incoming
            # parameters to sanitized Python values
            new_params = validation.validators.to_python(params, formencode_state)

        elif (hasattr(validation.validators, 'validate')
              and getattr(validation, 'needs_controller', False)):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(
                controller, params, formencode_state)

        elif hasattr(validation.validators, 'validate'):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(params, formencode_state)

        # Theoretically this should not happen...
        # if new_params is None:
        #     return params

        return new_params

    def _render_response(self, tgl, controller, response):
        """
        Render response takes the dictionary returned by the
        controller calls the appropriate template engine. It uses
        information off of the decoration object to decide which engine
        and template to use, and removes anything in the exclude_names
        list from the returned dictionary.

        The exclude_names functionality allows you to pass variables to
        some template rendering engines, but not others. This behavior
        is particularly useful for rendering engines like JSON or other
        "web service" style engines which don't use and explicit
        template, or use a totally generic template.

        All of these values are populated into the context object by the
        expose decorator.
        """

        req = tgl.request
        resp = tgl.response

        (content_type, engine_name, template_name, exclude_names, render_params
            ) = controller.decoration.lookup_template_engine(tgl)

        result = dict(response=response, content_type=content_type,
                      engine_name=engine_name, template_name=template_name)

        if content_type is not None:
            resp.headers['Content-Type'] = content_type

        # if it's a string return that string and skip all the stuff
        if not isinstance(response, dict):
            if engine_name == 'json' and isinstance(response, list):
                raise JsonEncodeError(
                    'You may not expose with JSON a list return value because'
                    ' it leaves your application open to CSRF attacks.')
            return result

        # Save these objects as locals from the SOP to avoid expensive lookups
        tmpl_context = tgl.tmpl_context

        # If there is an identity, push it to the Pylons template context
        tmpl_context.identity = req.environ.get('repoze.who.identity')

        # Setup the template namespace, removing anything that the user
        # has marked to be excluded.
        namespace = response
        for name in exclude_names:
            namespace.pop(name, None)

        # If we are in a test request put the namespace where it can be
        # accessed directly
        if 'paste.testing' in req.environ:
            testing_variables = req.environ['paste.testing_variables']
            testing_variables['namespace'] = namespace
            testing_variables['template_name'] = template_name
            testing_variables['exclude_names'] = exclude_names
            testing_variables['render_params'] = render_params
            testing_variables['controller_output'] = response

        # Render the result.
        rendered = tg_render(template_vars=namespace, template_engine=engine_name,
                             template_name=template_name, **render_params)

        result['response'] = rendered
        return result

    def _handle_validation_errors(self,
            controller, remainder, params, exception):
        """Handle validation errors.

        Sets up tg.tmpl_context.form_values
        and tg.tmpl_context.form_errors
        to assist generating a form with given values
        and the validation failure messages.

        The error handler in decoration.validation.error_handler is called.
        If an error_handler isn't given, the original controller is used
        as the error handler instead.

        """
        tmpl_context = tg.tmpl_context
        tmpl_context.validation_exception = exception
        tmpl_context.form_errors = {}

        if isinstance(exception, _Tw2ValidationError):
            #Fetch all the children and grandchildren of a widget
            widget = exception.widget
            widget_children = _navigate_tw2form_children(widget.child)

            errors = [(child.key, child.error_msg) for child in widget_children]
            tmpl_context.form_errors.update(errors)
            tmpl_context.form_values = widget.child.value
        elif isinstance(exception, TGValidationError):
            tmpl_context.form_errors = exception.error_dict
            tmpl_context.form_values = exception.value
        else:
            # Most Invalid objects come back with a list of errors in the format:
            #"fieldname1: error\nfieldname2: error"
            error_list = exception.__str__().split('\n')
            for error in error_list:
                field_value = map(strip_string, error.split(':', 1))

                #if the error has no field associated with it,
                #return the error as a global form error
                if len(field_value) == 1:
                    tmpl_context.form_errors['_the_form'] = field_value[0]
                    continue

                tmpl_context.form_errors[field_value[0]] = field_value[1]

            tmpl_context.form_values = getattr(exception, 'value', {})

        error_handler = controller.decoration.validation.error_handler
        if error_handler is None:
            error_handler = controller
            output = error_handler(*remainder, **dict(params))
        else:
            output = error_handler(im_self(controller), *remainder, **dict(params))

        return error_handler, output

    def _initialize_validation_context(self, tgl):
        tgl.tmpl_context.form_errors = {}
        tgl.tmpl_context.form_values = {}

    def _check_security(self):
        predicate = getattr(self, 'allow_only', None)
        if predicate is None:
            return True
        try:
            predicate.check_authorization(tg.request.environ)
        except NotAuthorizedError as e:
            reason = unicode_text(e)
            if hasattr(self, '_failed_authorization'):
                # Should shortcircuit the rest, but if not we will still
                # deny authorization
                self._failed_authorization(reason)
            if not_anonymous().is_met(tg.request.environ):
                # The user is authenticated but not allowed.
                code = 403
                status = 'error'
            else:
                # The user has not been not authenticated.
                code = 401
                status = 'warning'
            tg.response.status = code
            flash(reason, status=status)
            abort(code, comment=reason)

__all__ = ['DecoratedController']
