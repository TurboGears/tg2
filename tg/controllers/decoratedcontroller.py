# -*- coding: utf-8 -*-
"""
This module defines the class for decorating controller methods so that on
call the methods can be expressed using expose, validate, and other
decorators to effect a rendered page.
"""

import inspect

import formencode
import pylons
from pylons import config, request
from pylons.controllers.util import abort

from repoze.what.predicates import NotAuthorizedError, not_anonymous
import tw

from tg.render import render as tg_render
from tg.decorators import expose
from tg.flash import flash

from util import pylons_formencode_gettext

# @expose(content_type=CUSTOM_CONTENT_TYPE) won't
# override pylons.request.content_type
CUSTOM_CONTENT_TYPE = 'CUSTOM/LEAVE'

class DecoratedController(object):
    """Creates an interface to hang decoration attributes on
    controller methods for the purpose of rendering web content.
    """
    def __init__(self, *args, **kwargs):
        if hasattr(self, 'allow_only') and self.allow_only is not None:
            # Let's turn Controller.allow_only into something useful for
            # the @allow_only decorator.
            predicate = self.allow_only
            #self = allow_only(predicate)(self)
        super(DecoratedController, self).__init__(*args, **kwargs)

    def _is_exposed(self, controller, name):
        if hasattr(controller, name):
            method = getattr(controller, name)
            if inspect.ismethod(method) and hasattr(method, 'decoration'):
                return method.decoration.exposed

    def _call(self, controller, params, remainder=None):
        """
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
        pylons.request.start_response = self.start_response

        remainder = remainder or []
        try:
            pylons.request.headers['tg_format'] = params.get('tg_format', None)

            controller.decoration.run_hooks('before_validate', remainder,
                                            params)
            for ignore in config.get('ignore_parameters', []):
                if params.get(ignore):
                    del params[ignore]

            # Validate user input
            params = self._perform_validate(controller, params)

            pylons.c.form_values = params

            controller.decoration.run_hooks('before_call', remainder, params)
            # call controller method

            output = controller(*remainder, **dict(params))

        except formencode.api.Invalid, inv:
            controller, output = self._handle_validation_errors(controller,
                                                                remainder,
                                                                params, inv)

        # Render template
        controller.decoration.run_hooks('before_render', remainder, params,
                                        output)
        response = self._render_response(controller, output)
        controller.decoration.run_hooks('after_render', response)
        return response


    def _perform_validate(self, controller, params):
        """
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

        # this is here because the params were not getting passed in on controllers that
        # were mapped with routes.  This is a fix, but it's in the wrong place.
        # we need to add better tests to ensure decorated controllers with routings work
        # properly.
        if isinstance(controller.im_self, DecoratedController):
            params.update(pylons.request.params.mixed())

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
            new_params = validation.validators.validate(controller, params, state)

        elif hasattr(validation.validators, 'validate'):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(params, state)

        # Theoretically this should not happen...
        #if new_params is None:
        #    return params

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

        # skip all the complicated stuff if we're don't have a response dict
        # to work with.
        if not isinstance(response, dict):
            return response


        content_type, engine_name, template_name, exclude_names = \
            controller.decoration.lookup_template_engine(pylons.request)

        pylons.response.headers['Content-Type'] = content_type

        # Save these objeccts as locals from the SOP to avoid expensive lookups
        req = pylons.request._current_obj()
        tmpl_context = pylons.tmpl_context._current_obj()
        use_legacy_renderer = pylons.config.get("use_legacy_renderer", True)

        #what causes this condition?  there are no tests for it.
        if template_name is None:
            return response

        # Prepare the engine, if it's not already been prepared.
        # json is a buffet engine ATM
        if use_legacy_renderer or 'json' == engine_name:
            # get the buffet handler
            buffet = pylons.buffet._current_obj()

            if engine_name not in _configured_engines():
                template_options = dict(config).get('buffet.template_options', {})
                buffet.prepare(engine_name, **template_options)
                _configured_engines().add(engine_name)

        #if there is an identity, push it to the pylons template context
        tmpl_context.identity = req.environ.get('repoze.who.identity')

        #set up the tw renderer
        if engine_name in 'genshi' or 'mako':
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
            testing_variables['controller_output'] = response

        # Render the result.
        if use_legacy_renderer or 'json' == engine_name:
            result = buffet.render(engine_name=engine_name,
                               template_name=template_name,
                               include_pylons_variables=False,
                               namespace=namespace)
        else:
            result = tg_render(template_vars=namespace,
                      template_engine=engine_name,
                      template_name=template_name)

        return result

    def _handle_validation_errors(self, controller, remainder, params, exception):
        """
        Sets up pylons.c.form_values and pylons.c.form_errors to assist
        generating a form with given values and the validation failure
        messages.

        The error handler in decoration.validation.error_handler is called. If
        an error_handler isn't given, the original controller is used as the
        error handler instead.
        """

        pylons.c.validation_exception = exception
        pylons.c.form_errors = {}

        # Most Invalid objects come back with a list of errors in the format:
        #"fieldname1: error\nfieldname2: error"

        error_list = exception.__str__().split('\n')

        for error in error_list:
            field_value = error.split(':')

            #if the error has no field associated with it,
            #return the error as a global form error
            if len(field_value) == 1:
                pylons.c.form_errors['_the_form'] = field_value[0].strip()
                continue

            pylons.c.form_errors[field_value[0]] = field_value[1].strip()

        pylons.c.form_values = exception.value

        error_handler = controller.decoration.validation.error_handler
        if error_handler is None:
            error_handler = controller
            output = error_handler(*remainder, **dict(params))
        elif hasattr(error_handler, 'im_self') and error_handler.im_self != controller:
            output = error_handler(*remainder, **dict(params))
        else:
            output = error_handler(controller.im_self, *remainder, **dict(params))

        return error_handler, output

    def _initialize_validation_context(self):
        pylons.c.form_errors = {}
        pylons.c.form_values = {}

    def _check_security(self):
        predicate = getattr(self, 'allow_only', None)
        if predicate is None:
            return True
        try:
            predicate.check_authorization(pylons.request.environ)
        except NotAuthorizedError, e:
            reason = unicode(e)
            if hasattr(self, '_failed_authorization'):
                # Should shortcircut the rest, but if not we will still
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

def _configured_engines():
    """
    Returns a set containing the names of the currently configured template
    engines from the active application's globals
    """
    g = pylons.app_globals._current_obj()
    if not hasattr(g, 'tg_configured_engines'):
        g.tg_configured_engines = set()
    return g.tg_configured_engines

__all__ = [
    "DecoratedController"
    ]
