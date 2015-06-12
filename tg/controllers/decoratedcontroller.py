# -*- coding: utf-8 -*-
"""
This module defines the class for decorating controller methods so that on
call the methods can be expressed using expose, validate, and other
decorators to effect a rendered page.
"""

import inspect, operator
import warnings
import tg
from tg.controllers.util import abort
from tg.predicates import NotAuthorizedError, not_anonymous

from crank.util import (get_params_with_argspec,
                        remove_argspec_params_from_params)

from tg.flash import flash
from tg.jsonify import JsonEncodeError
from tg.render import render as tg_render
from tg.validation import (_navigate_tw2form_children,
                           _Tw2ValidationError, validation_errors,
                           TGValidationError, _ValidationStatus)

from tg._compat import unicode_text, with_metaclass, im_self, url2pathname, default_im_func
from functools import partial

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

    def _call(self, controller, params, remainder=None, context=None):
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
        if context is None: #pragma: no cover
            #compatibility with old code that didn't pass request locals explicitly
            context = tg.request.environ['tg.locals']

        hooks = tg.hooks
        context_config = tg.config._current_obj()
        context.request._fast_setattr('validation', _ValidationStatus())

        #This is necessary to prevent spurious Content Type header which would
        #cause problems to paste.response.replace_header calls and cause
        #responses wihout content type to get out with a wrong content type
        resp_headers = context.response.headers
        if not resp_headers.get('Content-Type'):
            resp_headers.pop('Content-Type', None)

        if remainder:
            remainder = tuple(map(url2pathname, remainder or []))
        else:
            remainder = tuple()

        hooks.notify('before_validate', args=(remainder, params),
                     controller=controller, context_config=context_config)

        try:
            validate_params = get_params_with_argspec(controller, params, remainder)

            # Validate user input
            params = self._perform_validate(controller, validate_params, context)
            context.request.validation.values = params

            params, remainder = remove_argspec_params_from_params(controller, params, remainder)
            bound_controller_callable = controller
        except validation_errors as inv:
            instance, controller = self._process_validation_errors(controller,
                                                                   remainder, params,
                                                                   inv, context=context)
            bound_controller_callable = partial(controller, instance)

        hooks.notify('before_call', args=(remainder, params),
                     controller=controller, context_config=context_config)

        # call controller method with applied wrappers
        controller_caller = controller.decoration.controller_caller
        output = controller_caller(context_config, bound_controller_callable, remainder, params)

        # Render template
        hooks.notify('before_render', args=(remainder, params, output),
                     controller=controller, context_config=context_config)

        response = self._render_response(context, controller, output)

        hooks.notify('after_render', args=(response,),
                     controller=controller, context_config=context_config)

        return response['response']

    @classmethod
    def _perform_validate(cls, controller, params, context=None):
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
        if context is None:  # pragma: no cover
            warnings.warn("Calling DecoratedController._perform_validate without a Context is now deprecated."
                          " Please provide the context argument when calling it.",
                          DeprecationWarning)
            context = tg.request.environ['tg.locals']

        validations = controller.decoration.validations
        if not validations:
            return params

        req = context.request
        validation_status = req.validation

        validated_params = params
        for validation_intent in validations:
            validation_status.intent = validation_intent
            validated_params = validation_intent.check(controller, validated_params)
        return validated_params

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

    @classmethod
    def _process_validation_errors(cls, controller, remainder, params, exception, context):
        """Process validation errors.

        Sets up validation status and error tracking
        to assist generating a form with given values
        and the validation failure messages.

        The error handler in decoration.validation.error_handler resolved
        and returned to be called as a controller.
        If an error_handler isn't given, the original controller is returned instead.

        """
        req = context.request

        validation_status = req.validation
        validation_status.exception = exception

        if isinstance(exception, _Tw2ValidationError):
            # Fetch all the children and grandchildren of a widget
            widget = exception.widget
            widget_children = _navigate_tw2form_children(widget.child)

            errors = dict((child.compound_key, child.error_msg) for child in widget_children)
            validation_status.errors = errors
            validation_status.values = widget.child.value
        elif isinstance(exception, TGValidationError):
            validation_status.errors = exception.error_dict
            validation_status.values = exception.value
        else:
            # Most Invalid objects come back with a list of errors in the format:
            # "fieldname1: error\nfieldname2: error"
            error_list = exception.__str__().split('\n')
            for error in error_list:
                field_value = list(map(strip_string, error.split(':', 1)))

                #if the error has no field associated with it,
                #return the error as a global form error
                if len(field_value) == 1:
                    validation_status.errors['_the_form'] = field_value[0]
                    continue

                validation_status.errors[field_value[0]] = field_value[1]

            validation_status.values = getattr(exception, 'value', {})

        # Get the error handler associated to the current validation status.
        error_handler = validation_status.error_handler
        if error_handler is None:
            error_handler = default_im_func(controller)

        return im_self(controller), error_handler

    @classmethod
    def _handle_validation_errors(cls, controller, remainder, params, exception, tgl=None):
        """Handle validation errors.

        Processes validation errors and call the error_handler,
        this is not used by TurboGears itself and is mostly provided
        for backward compatibility.
        """
        warnings.warn("DecoratedController._handle_validation_errors is deprecated and will be removed",
                      DeprecationWarning)

        if tgl is None:  # pragma: no cover
            # compatibility with old code that didn't pass request locals explicitly
            tgl = tg.request.environ['tg.locals']

        obj, error_handler = cls._process_validation_errors(controller, remainder, params,
                                                            exception, tgl)
        return error_handler, error_handler(obj, *remainder, **dict(params))

    def _check_security(self):
        requirement = getattr(self, 'allow_only', None)
        if requirement is None:
            return True

        if hasattr(requirement, 'predicate'):
            # It is a full requirement, let it build the response
            requirement._check_authorization()
            return True

        # It is directly a predicate, build the response ourselves
        predicate = requirement
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
