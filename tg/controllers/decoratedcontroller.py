# -*- coding: utf-8 -*-
"""
This module defines the class for decorating controller methods so that on
call the methods can be expressed using expose, validate, and other
decorators to effect a rendered page.
"""

import inspect
import urllib.request
from functools import partial

from crank.util import flatten_arguments, get_params_with_argspec

import tg
from tg.configuration.utils import TGConfigError
from tg.flash import flash
from tg.predicates import NotAuthorizedError, not_anonymous
from tg.render import render as tg_render
from tg.request_local import request as tg_request
from tg.request_local import response as tg_response
from tg.util.instance_method import default_im_func, im_self
from tg.validation import _ValidationStatus

from .util import abort


class _DecoratedControllerMeta(type):
    def __init__(cls, name, bases, attrs):
        super(_DecoratedControllerMeta, cls).__init__(name, bases, attrs)
        for name, value in attrs.items():
            # Inherit decorations for methods exposed with inherit=True
            if hasattr(value, "decoration") and value.decoration.inherit:
                for pcls in reversed(bases):
                    parent_method = getattr(pcls, name, None)
                    if parent_method and hasattr(parent_method, "decoration"):
                        value.decoration.merge(parent_method.decoration)


class DecoratedController(object, metaclass=_DecoratedControllerMeta):
    """Decorated controller object.

    Creates an interface to hang decoration attributes on
    controller methods for the purpose of rendering web content.

    """

    def _is_exposed(self, controller, name):
        method = getattr(controller, name, None)
        if method and inspect.ismethod(method) and hasattr(method, "decoration"):
            return method.decoration.exposed

    def _call(self, action, params, remainder=None, context=None):
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
        if context is None:  # pragma: no cover
            # compatibility with old code that didn't pass request locals explicitly
            context = tg_request.environ["tg.locals"]

        hooks = tg.hooks
        context_config = context.config
        context.request._fast_setattr("validation", _ValidationStatus())

        # This is necessary to prevent spurious Content Type header which would
        # cause problems to paste.response.replace_header calls and cause
        # responses without content type to get out with a wrong content type
        resp_headers = context.response.headers
        if not resp_headers.get("Content-Type"):
            resp_headers.pop("Content-Type", None)

        if remainder:
            remainder = tuple(map(urllib.request.url2pathname, remainder or []))
        else:
            remainder = tuple()

        hooks.notify("before_validate", args=(remainder, params), controller=action)

        validate_params = get_params_with_argspec(action, params, remainder)
        context.request.args_params = (
            validate_params  # Update args_params with positional args
        )
        validation_exceptions = tuple(
            context_config.get("validation.exceptions", tuple())
        )

        try:
            params = self._perform_validate(action, validate_params, context)
        except validation_exceptions as inv:
            instance, error_handler, chain_validation = self._process_validation_errors(
                action, remainder, params, inv, context=context
            )
            while chain_validation:
                # The validation asked for chained validation,
                # go on and validate the error_handler too.
                try:
                    params = self._perform_validate(
                        error_handler, validate_params, context
                    )
                except validation_exceptions as inv:
                    instance, error_handler, chain_validation = (
                        self._process_validation_errors(
                            error_handler, remainder, params, inv, context=context
                        )
                    )
                else:
                    chain_validation = False
            action = error_handler
            bound_controller_callable = partial(error_handler, instance)
        else:
            bound_controller_callable = action
            context.request.validation.values = params
            remainder, params = flatten_arguments(action, params, remainder)

        hooks.notify("before_call", args=(remainder, params), controller=action)

        # call controller method with applied wrappers
        controller_caller = action.decoration.controller_caller
        output = controller_caller(
            context_config, bound_controller_callable, remainder, params
        )

        # Render template
        hooks.notify(
            "before_render", args=(remainder, params, output), controller=action
        )

        response = self._render_response(context, action, output)

        hooks.notify("after_render", args=(response,), controller=action)

        return response["response"]

    @classmethod
    def _perform_validate(cls, controller, params, context):
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
        validations = controller.decoration.validations
        if not validations:
            return params

        req = context.request
        validation_status = req.validation
        config = context.config

        validated_params = params
        for validation_intent in validations:
            validation_status.intent = validation_intent
            validated_params = validation_intent.check(
                config, controller, validated_params
            )
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

        (
            engine_content_type,
            engine_name,
            template_name,
            exclude_names,
            render_params,
        ) = controller.decoration.lookup_template_engine(tgl)

        result = dict(
            response=response,
            content_type=engine_content_type,
            engine_name=engine_name,
            template_name=template_name,
        )

        if resp.content_type is None and engine_content_type is not None:
            # User didn't set a specific content type during controller
            # and template engine has a suggested one. Use template engine one.
            resp.headers["Content-Type"] = engine_content_type

            content_type = resp.headers["Content-Type"]
            if "charset" not in content_type and (
                content_type.startswith("text")
                or content_type
                in ("application/xhtml+xml", "application/xml", "application/json")
            ):
                resp.content_type = content_type + "; charset=utf-8"

        # if it's a string return that string and skip all the stuff
        if not isinstance(response, dict):
            return result

        # Setup the template namespace, removing anything that the user
        # has marked to be excluded.
        namespace = response
        for name in exclude_names:
            namespace.pop(name, None)

        # If we are in a test request put the namespace where it can be
        # accessed directly
        if "paste.testing" in req.environ:
            testing_variables = req.environ["paste.testing_variables"]
            testing_variables["namespace"] = namespace
            testing_variables["template_name"] = template_name
            testing_variables["exclude_names"] = exclude_names
            testing_variables["render_params"] = render_params
            testing_variables["controller_output"] = response

        # Render the result.
        rendered = tg_render(
            template_vars=namespace,
            template_engine=engine_name,
            template_name=template_name,
            **render_params,
        )

        result["response"] = rendered
        return result

    @classmethod
    def _process_validation_errors(
        cls, controller, remainder, params, exception, context
    ):
        """Process validation errors.

        Sets up validation status and error tracking
        to assist generating a form with given values
        and the validation failure messages.

        The error handler in decoration.validation.error_handler resolved
        and returned to be called as a controller.
        If an error_handler isn't given, the original controller is returned instead.

        """
        req = context.request
        config = context.config

        validation_explode = config.get("validation.explode", {})
        validation_status = req.validation
        validation_status.exception = exception

        if isinstance(exception, tuple(validation_explode.keys())):
            exception_class = exception.__class__
            explode = None
            for supported_class in validation_explode:
                if issubclass(exception_class, supported_class):
                    explode = validation_explode[supported_class]

            if explode is None:
                raise TGConfigError(
                    f"No validation explode function found for: {exception_class}"
                )

            exploded_validation = explode(exception)
            validation_status.errors = exploded_validation["errors"]
            validation_status.values = exploded_validation["values"]
        else:
            raise TGConfigError(
                f"No validation explode function found for: {exception.__class__}"
            )

        # Get the error handler associated to the current validation status.
        error_handler = validation_status.error_handler
        chain_validation = validation_status.chain_validation
        if error_handler is None:
            error_handler = default_im_func(controller)
            chain_validation = False

        return im_self(controller), error_handler, chain_validation

    def _check_security(self):
        requirement = getattr(self, "allow_only", None)
        if requirement is None:
            return True

        if hasattr(requirement, "predicate"):
            # It is a full requirement, let it build the response
            requirement._check_authorization()
            return True

        # It is directly a predicate, build the response ourselves
        predicate = requirement
        try:
            predicate.check_authorization(tg_request.environ)
        except NotAuthorizedError as e:
            reason = str(e)
            if hasattr(self, "_failed_authorization"):
                # Should shortcircuit the rest, but if not we will still
                # deny authorization
                self._failed_authorization(reason)
            if not_anonymous().is_met(tg_request.environ):
                # The user is authenticated but not allowed.
                code = 403
                status = "error"
            else:
                # The user has not been not authenticated.
                code = 401
                status = "warning"
            tg_response.status = code
            flash(reason, status=status)
            abort(code, comment=reason)


__all__ = ["DecoratedController"]
