# -*- coding: utf-8 -*-
"""
This module defines the class for decorating controller methods so that on
call the methods can be expressed using expose, validate, and other
decorators to effect a rendered page.
"""

from urllib import url2pathname
import inspect

import formencode

try:
    from repoze.what.predicates import (
        NotAuthorizedError as WhatNotAuthorizedError, not_anonymous)
except ImportError:
    class WhatNotAuthorizedError(Exception):
        """Repoze.what not authorized error."""
    def not_anonymous():
        return False

import pylons
from pylons.configuration import config
from pylons import request
from pylons.controllers.util import abort

from tg.flash import flash
from tg.jsonify import JsonEncodeError
from tg.render import render as tg_render
from tg.controllers.util import pylons_formencode_gettext

# Load tw (ToscaWidets) only on demand
tw = None

# @expose(content_type=CUSTOM_CONTENT_TYPE) won't
# override pylons.request.content_type
CUSTOM_CONTENT_TYPE = 'CUSTOM/LEAVE'


class NotAuthorizedError(Exception):
    """Not authorized error."""


class DecoratedController(object):
    """Decorated controller object.

    Creates an interface to hang decoration attributes on
    controller methods for the purpose of rendering web content.

    """

    def _is_exposed(self, controller, name):
        if hasattr(controller, name):
            method = getattr(controller, name)
            if inspect.ismethod(method) and hasattr(method, 'decoration'):
                return method.decoration.exposed

    def _call(self, controller, params, remainder=None):
        """Run the controller with the given parameters.

        _call is called by _perform_call in Pylons' WSGIController.

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

        self._initialize_validation_context()

        #This is necessary to prevent spurious Content Type header which would
        #cause problems to paste.response.replace_header calls and cause
        #responses wihout content type to get out with a wrong content type
        if not pylons.response.headers.get('Content-Type'):
            pylons.response.headers.pop('Content-Type', None)

        pylons.request.start_response = getattr(self, 'start_response', None)

        remainder = map(url2pathname, remainder or [])

        tg_decoration = controller.decoration
        try:
            if 'tg_format' in params:
                pylons.request.headers['tg_format'] = params['tg_format']

            tg_decoration.run_hooks('before_validate', remainder, params)

            validate_params = self._get_params_with_argspec(controller, params, remainder)

            for ignore in config.get('ignore_parameters', []):
                if params.get(ignore):
                    del params[ignore]

            # Validate user input
            params = self._perform_validate(controller, validate_params)

            pylons.tmpl_context.form_values = params

            tg_decoration.run_hooks('before_call', remainder, params)

            params, remainder = self._remove_argspec_params_from_params(controller, params, remainder)

            #apply controller wrappers
            controller_callable = tg_decoration.wrap_controller(controller)

            # call controller method
            output = controller_callable(*remainder, **dict(params))

        except formencode.api.Invalid, inv:
            controller, output = self._handle_validation_errors(
                controller, remainder, params, inv)
        except Exception, e:
            if config.get('use_toscawidgets2'):
                from tw2.core import ValidationError
                if isinstance(e, ValidationError):
                    controller, output = self._handle_validation_errors(
                        controller, remainder, params, e)
                else:
                    raise
            else:
                raise

        #Be sure that we run hooks if the controller changed due to validation errors
        tg_decoration = controller.decoration

        # Render template
        tg_decoration.run_hooks('before_render', remainder, params, output)

        response = self._render_response(controller, output)

        tg_decoration.run_hooks('after_render', response)

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
        state = type('state', (),
                {'_': staticmethod(pylons_formencode_gettext)})

        #Initialize new_params -- if it never gets updated just return params
        new_params = {}

        # The validator may be a dictionary, a FormEncode Schema object, or any
        # object with a "validate" method.
        if isinstance(validation.validators, dict):
            # TG developers can pass in a dict of param names and FormEncode
            # validators.  They are applied one by one and builds up a new set
            # of validated params.

            errors = {}
            for field, validator in validation.validators.iteritems():
                try:
                    new_params[field] = validator.to_python(params.get(field),
                            state)
                # catch individual validation errors into the errors dictionary
                except formencode.api.Invalid, inv:
                    errors[field] = inv

            # Parameters that don't have validators are returned verbatim
            for param, param_value in params.items():
                if not param in new_params:
                    new_params[param] = param_value

            # If there are errors, create a compound validation error based on
            # the errors dictionary, and raise it as an exception
            if errors:
                raise formencode.api.Invalid(
                    formencode.schema.format_compound_error(errors),
                    params, None, error_dict=errors)

        elif isinstance(validation.validators, formencode.Schema):
            # A FormEncode Schema object - to_python converts the incoming
            # parameters to sanitized Python values
            new_params = validation.validators.to_python(params, state)

        elif (hasattr(validation.validators, 'validate')
              and getattr(validation, 'needs_controller', False)):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(
                controller, params, state)

        elif hasattr(validation.validators, 'validate'):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(params, state)

        # Theoretically this should not happen...
        # if new_params is None:
        #     return params

        return new_params

    def _render_response(self, controller, response):
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

        req = pylons.request._current_obj()
        resp = pylons.response._current_obj()

        (content_type, engine_name, template_name, exclude_names, render_params
            ) = controller.decoration.lookup_template_engine(req)

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
        tmpl_context = pylons.tmpl_context._current_obj()
        use_legacy_renderer = pylons.configuration.config.get(
            'use_legacy_renderer', True)

        # what causes this condition?  there are no tests for it.
        # this is caused when someone specifies a content_type, but no template
        # because their controller returns a string.
        if template_name is None:
            return result

        # Prepare the engine, if it's not already been prepared.
        # To be removed? Buffet is not included in Pylons 1.0 any more!
        if use_legacy_renderer == engine_name:
            # get the buffet handler
            buffet = pylons.buffet._current_obj()
            if engine_name not in _configured_engines():
                template_options = config.get('buffet.template_options', {})
                buffet.prepare(engine_name, **template_options)
                _configured_engines().add(engine_name)

        # If there is an identity, push it to the Pylons template context
        tmpl_context.identity = req.environ.get('repoze.who.identity')

        # Set up the ToscaWidgets renderer
        if engine_name in ('genshi','mako') and config['use_toscawidgets']:
            global tw
            if not tw:
                try:
                    import tw
                except ImportError:
                    pass
            if tw:
                tw.framework.default_view = engine_name

        # Setup the template namespace, removing anything that the user
        # has marked to be excluded.
        namespace = dict(tmpl_context=tmpl_context)
        if isinstance(response, dict):
            namespace.update(response)

        for name in exclude_names:
            namespace.pop(name)

        # If we are in a test request put the namespace where it can be
        # accessed directly
        if req.environ.get('paste.testing'):
            testing_variables = req.environ['paste.testing_variables']
            testing_variables['namespace'] = namespace
            testing_variables['template_name'] = template_name
            testing_variables['exclude_names'] = exclude_names
            testing_variables['render_params'] = render_params
            testing_variables['controller_output'] = response

        # Render the result.
        if use_legacy_renderer == engine_name:
            rendered = buffet.render(engine_name=engine_name,
                template_name=template_name, include_pylons_variables=False,
                namespace=namespace, **render_params)
        else:
            rendered = tg_render(template_vars=namespace,
                template_engine=engine_name, template_name=template_name,
                **render_params)

        if isinstance(result, unicode) and not pylons.response.charset:
            resp.charset = 'UTF-8'

        result['response'] = rendered
        return result

    def _handle_validation_errors(self,
            controller, remainder, params, exception):
        """Handle validation errors.

        Sets up pylons.tmpl_context.form_values
        and pylons.tmpl_context.form_errors
        to assist generating a form with given values
        and the validation failure messages.

        The error handler in decoration.validation.error_handler is called.
        If an error_handler isn't given, the original controller is used
        as the error handler instead.

        """

        pylons.tmpl_context.validation_exception = exception
        pylons.tmpl_context.form_errors = {}

        # Most Invalid objects come back with a list of errors in the format:
        #"fieldname1: error\nfieldname2: error"

        error_list = exception.__str__().split('\n')

        for error in error_list:
            field_value = error.split(':', 1)

            #if the error has no field associated with it,
            #return the error as a global form error
            if len(field_value) == 1:
                pylons.tmpl_context.form_errors[
                    '_the_form'] = field_value[0].strip()
                continue

            pylons.tmpl_context.form_errors[
                field_value[0]] = field_value[1].strip()

        pylons.tmpl_context.form_values = getattr(exception, 'value', {})

        error_handler = controller.decoration.validation.error_handler
        if error_handler is None:
            error_handler = controller
            output = error_handler(*remainder, **dict(params))
        elif hasattr(error_handler, 'im_self'
                ) and error_handler.im_self != controller:
            output = error_handler(
                error_handler.im_self, *remainder, **dict(params))
        else:
            output = error_handler(
                controller.im_self, *remainder, **dict(params))

        return error_handler, output

    def _initialize_validation_context(self):
        pylons.tmpl_context.form_errors = {}
        pylons.tmpl_context.form_values = {}

    def _check_security(self):
        predicate = getattr(self, 'allow_only', None)
        if predicate is None:
            return True
        try:
            predicate.check_authorization(pylons.request.environ)
        except WhatNotAuthorizedError, e:
            reason = unicode(e)
            if hasattr(self, '_failed_authorization'):
                # Should shortcircuit the rest, but if not we will still
                # deny authorization
                self._failed_authorization(reason)
            if not_anonymous().is_met(request.environ):
                # The user is authenticated but not allowed.
                code = 403
                status = 'error'
            else:
                # The user has not been not authenticated.
                code = 401
                status = 'warning'
            pylons.response.status = code
            flash(reason, status=status)
            abort(code, comment=reason)
        except NotAuthorizedError, e:
            reason = getattr(e, 'msg',
                'You are not authorized to access this resource')
            code = getattr(e, 'code', 401)
            status = getattr(e, 'status', 'error')
            pylons.response.status = code
            flash(reason, status=status)
            abort(code, comment=reason)


def _configured_engines():
    """Get the configured engines.

    Returns a set containing the names of the currently configured template
    engines from the active application's globals.

    """
    g = pylons.app_globals._current_obj()
    if not hasattr(g, 'tg_configured_engines'):
        g.tg_configured_engines = set()
    return g.tg_configured_engines


__all__ = ['DecoratedController']
