# -*- coding: utf-8 -*-
"""
Controller Classes, dispatch methods and helper functions for controller operation.

This module contains the main classes which describe Turbogears2 Controllers.
These Controllers are handled by the Dispatch functions which are also provided here.

Lastly, url definition and browser redirection are defined here.
"""

import logging
import warnings
import urlparse, urllib
import mimetypes
import inspect

import formencode
import pylons
from pylons import url as pylons_url, config, request
from pylons.controllers import WSGIController
from pylons.controllers.util import abort

from repoze.what.predicates import NotAuthorizedError, not_anonymous
import tw

from tg.exceptions import (HTTPFound, HTTPNotFound, HTTPException,
    HTTPClientError)
from tg.render import render as tg_render
from tg.decorators import expose, allow_only
from tg.i18n import setup_i18n
from tg.flash import flash

from webob import Request
from webob.exc import HTTPUnauthorized

log = logging.getLogger(__name__)

# If someone goes @expose(content_type=CUSTOM_CONTENT_TYPE)
# then we won't override request.content_type
CUSTOM_CONTENT_TYPE = 'CUSTOM/LEAVE'

def _configured_engines():
    """
    Returns a set containing the names of the currently configured template
    engines from the active application's globals
    """
    g = pylons.app_globals._current_obj()
    if not hasattr(g, 'tg_configured_engines'):
        g.tg_configured_engines = set()
    return g.tg_configured_engines


class DecoratedController(WSGIController):
    """
    DecoratedController takes action on the decorated controller methods
    created by the decorators in tg.decorators.

    The decorators in tg.decorators create an attribute named 'decoration' on
    the controller method, creating rules as to:

    1) how to validate the request,
    2) how to render the response,
    3) allowing hooks to be registered to happen:

        a) before validation
        b) before the controller method is called
        c) before the rendering takes place, and
        d) after the rendering has happened.
    """

    def __init__(self, *args, **kwargs):
        if hasattr(self, 'allow_only') and self.allow_only is not None:
            # Let's turn Controller.allow_only into something useful for
            # the @allow_only decorator.
            predicate = self.allow_only
            self = allow_only(predicate)(self)
        super(DecoratedController, self).__init__(*args, **kwargs)

    def __before__(self, *args, **kw):
        """
        Override this method to define any action you would like taken
        before the controller code is executed.  This is particularly useful
        for defining a Controller-wide specification (all methods) for things like:
        setting up variables/objects in the template context,
        restricting access, or other tasks which should be executed
        before the controller method is called.
        """

    def __after__(self, *args, **kw):
        """Override this method to define what you would like to run after the
        template has been rendered. This method will
        always be run after your method, even if it raises an Exception or redirects.

        An example use-case would be a runtime-specific template change,
        you where would want to change the template back to the originally
        decorated template after you have temporarily changed it.
        """
    def _get_argspec(self, func):
        try:
            cached_argspecs = self.__class__._cached_argspecs
        except AttributeError:
            self.__class__._cached_argspecs = cached_argspecs = {}

        try:
            argspec = cached_argspecs[func.im_func]
        except KeyError:
            argspec = cached_argspecs[func.im_func] = inspect.getargspec(func)
        return argspec

    def _perform_call(self, controller, params, remainder=None):
        """
        _perform_call is called by _inspect_call in Pylons' WSGIController.

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
        request.start_response = self.start_response

        remainder = remainder or []
        try:
            if 'tg_format' in params:
                request.headers['tg_format'] = params['tg_format']

            controller.decoration.run_hooks('before_validate', remainder,
                                            params)
            for ignore in config.get('ignore_parameters', []):
                if params.get(ignore):
                    del params[ignore]

            validate_params = params.copy()
            argspec = self._get_argspec(controller)
            argvars = argspec[0][1:]
            if argvars and enumerate(remainder):
                for i, var in enumerate(argvars):
                    if i>= len(remainder):
                        break
                    validate_params[var] = remainder[i]

            # Validate user input
            params = self._perform_validate(controller, validate_params)

            pylons.c.form_values = params

            controller.decoration.run_hooks('before_call', remainder, params)
            # call controller method

            argvars = argspec[0][1:]
            if argvars:
                for i, var in enumerate(remainder):
                    if i>=len(argvars):
                        break;
                    name = argvars[i]
                    if name in params:
                        remainder[i] = params[name]
                        del params[name]
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
                    # XXX: Is this necessary to call twice?
                    #validator.to_python(params.get(field), state)
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

        content_type, engine_name, template_name, exclude_names = \
            controller.decoration.lookup_template_engine(request)

        if content_type != CUSTOM_CONTENT_TYPE:
            pylons.response.headers['Content-Type'] = content_type

        # skip all the complicated stuff if we're don't have a response dict
        # to work with.
        if not isinstance(response, dict):
            return response

        # Save these objeccts as locals from the SOP to avoid expensive lookups
        req = request._current_obj()
        tmpl_context = pylons.tmpl_context._current_obj()
        use_legacy_renderer = config.get("use_legacy_renderer", True)

        # what causes this condition?  there are no tests for it.
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

        # if there is an identity, push it to the pylons template context
        tmpl_context.identity = req.environ.get('repoze.who.identity')

        # set up the tw renderer
        if config.get('use_toscawidgets', True) and engine_name in ('genshi', 'mako'):
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

class ObjectDispatchController(DecoratedController):
    """
    Object dispatch (also "object publishing") means that each portion of the
    URL becomes a lookup on an object.  The next part of the URL applies to the
    next object, until you run out of URL.  Processing starts on a "Root"
    object.

    Thus, /foo/bar/baz become URL portion "foo", "bar", and "baz".  The
    dispatch looks for the "foo" attribute on the Root URL, which returns
    another object.  The "bar" attribute is looked for on the new object, which
    returns another object.  The "baz" attribute is similarly looked for on
    this object.

    Dispatch does not have to be directly on attribute lookup, objects can also
    have other methods to explain how to dispatch from them.  The search ends
    when a decorated controller method is found.

    The rules work as follows:

    1) If the current object under consideration is a decorated controller
       method, the search is ended.

    2) If the current object under consideration has a "default" method, keep a
       record of that method.  If we fail in our search, and the most recent
       method recorded is a "default" method, then the search is ended with
       that method returned.

    3) If the current object under consideration has a "lookup" method, keep a
       record of that method.  If we fail in our search, and the most recent
       method recorded is a "lookup" method, then execute the "lookup" method,
       and start the search again on the return value of that method.

    4) If the URL portion exists as an attribute on the object in question,
       start searching again on that attribute.

    5) If we fail our search, try the most recent recorded methods as per 2 and
       3.
    """

    def _get_routing_info(self, url=None):
        """
        Returns a tuple (controller, remainder, params)

        :Parameters:
          url
            url as string
        """

        if url is None:
            url_path = request.path.split('/')[1:]
        else:
            url_path = url.split('/')

        controller, remainder = _object_dispatch(self, url_path)
        # XXX Place controller url at context temporarily... we should be
        #    really using SCRIPT_NAME for this.
        if remainder:
            pylons.c.controller_url = '/'.join(url_path[:-len(remainder)])
        else:
            pylons.c.controller_url = url
        if remainder and remainder[-1] == '':
            remainder.pop()
        return controller, remainder, request.params.mixed()

    def _perform_call(self, func, args):
        controller, remainder, params = self._get_routing_info(args.get('url'))
        func_name = func.__name__
        if func_name == '__before__' or func_name == '__after__':
            if func_name == '__before__' and hasattr(controller.im_class, '__before__'):
                return controller.im_self.__before__(*args)
            if func_name == '__after__' and hasattr(controller.im_class, '__after__'):
                return controller.im_self.__after__(*args)
            return
        return DecoratedController._perform_call(
            self, controller, params, remainder=remainder)

    def routes_placeholder(self, url='/', start_response=None, **kwargs):
        """
        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.
        """
        pass

def _check_controller_auth(obj):
    """this function checks if a controller has a 'alow_only' attribute and if
    it is the case, test that this require predicate can be evaled to True.
    It will raise a Forbidden exception if the predicate is not valid.
    """
    if hasattr(obj, "im_self"):
        klass_instance = obj.im_self
    else:
        klass_instance = obj

    if hasattr(klass_instance, "_check_security"):
        klass_instance._check_security()

def _object_dispatch(obj, url_path):
    remainder = url_path

    request.response_type = None
    request.response_ext = None
    # if the last item in the remainder has an extention
    # remove the extension, and add a response content type to the
    # request parameters
    if remainder and '.' in remainder[-1]:
        last_remainder = remainder[-1]
        mime_type, encoding = mimetypes.guess_type(last_remainder)
        if mime_type:
            extension_spot = last_remainder.rfind('.')
            extension = last_remainder[extension_spot:]
            remainder[-1] = last_remainder[:extension_spot]
            request.response_type = mime_type
            request.response_ext = extension

    notfound_handlers = []
    while True:
        try:
            obj, parent, remainder = _find_object(obj, remainder, notfound_handlers)

            return _find_restful_dispatch(obj, parent, remainder)

        # auth error should be treated separatly from "not found" errors
        except HTTPUnauthorized, httpe:
            log.debug("a 401 error occured for obj: %s" % obj)
            raise

        except HTTPException, e:
            if e.status_int != 404:
                raise e.exception

            if not notfound_handlers:
                raise e.exception

            name, obj, parent, remainder = notfound_handlers.pop()
            if name == 'default':
                return _find_restful_dispatch(obj, parent, remainder)
            else:
                obj, remainder = obj(*remainder)
                list(remainder)
                continue

def _find_restful_dispatch(obj, parent, remainder):

    _check_controller_auth(obj)
    if not inspect.isclass(obj) and not isinstance(obj, RestController):
        return obj, remainder

    request_method = method = request.method.lower()

    #conventional hack for handling methods which are not supported by most browsers
    params = request.params
    if '_method' in params:
        if params['_method']:
            method = params['_method'].lower()

    if remainder and remainder[-1] == '':
        remainder = remainder[:-1]
    if remainder:
        remainder_len = len(remainder)
        #dispatch is finished, and we are where we need to be
        if remainder_len <=2 and remainder[-1] in ['new', 'edit']:
            if method == 'get':
                method = remainder[-1]
            if method == 'edit' and len(remainder) <=2:
                remainder = remainder[:-1]
            if method == 'new' and len(remainder) == 1:
                remainder = remainder[:-1]
        elif remainder_len <=2 and remainder[-1] == 'delete':
            method = 'delete'
            if remainder_len <= 2:
                remainder = remainder[:-1]

        #handles put and post for parental relations
        elif remainder_len >=2 and (method == 'post' or method == 'put') and hasattr(obj, 'get_one'):
            func = getattr(obj, 'get_one')
            arg_len = len(inspect.getargspec(func)[0])-1
            new_remainder = remainder[arg_len:]
            if len(new_remainder) > 0 and hasattr(obj, new_remainder[0]):
                return _find_restful_dispatch(*_find_object(getattr(obj, new_remainder[0]), new_remainder[1:], []))
            elif hasattr(obj, remainder[0]):
                return _find_restful_dispatch(*_find_object(getattr(obj, remainder[0]), remainder[1:], []))
            else:
                raise HTTPNotFound().exception
        #handles new and edit for parental relations
        if remainder and hasattr(obj, remainder[0]) and remainder[0] not in ['new', 'edit']:
            #revert the dispatch back to object_dispatch
            if inspect.isclass(obj):
                obj = obj()
            return _find_restful_dispatch(*_find_object(getattr(obj, remainder[0]), remainder[1:], []))

    #support for get_all and get_one methods
    if not remainder and method == 'get' and hasattr(obj, 'get_all') and hasattr(obj.get_all, 'decoration') and obj.get_all.decoration.exposed:
        method = 'get_all'
    if len(remainder)>0 and method == 'get' and hasattr(obj, 'get_one') and hasattr(obj.get_all, 'decoration') and obj.get_one.decoration.exposed:
        if len(remainder) == 1:
            method = 'get_one'
        else:
            func = getattr(obj, 'get_one')
            arg_len = len(inspect.getargspec(func)[0])-1
            remainder = remainder[arg_len:]
            if len(remainder) > 0 and hasattr(obj, remainder[0]):
                return _find_restful_dispatch(*_find_object(getattr(obj, remainder[0]), remainder[1:], []))
            elif hasattr(obj, 'get_one') and inspect.getargspec(obj.get_one)[1]:
                method = 'get_one'
            else:
                raise HTTPNotFound().exception

    #support for get_delete and post_delete methods
    if request_method == 'get' and method == 'delete' and hasattr(obj, 'get_delete') and hasattr(obj.get_delete, 'decoration') and obj.get_delete.decoration.exposed:
        method = 'get_delete'
    if request_method == 'post' and method == 'delete' and hasattr(obj, 'post_delete') and hasattr(obj.post_delete, 'decoration')and obj.post_delete.decoration.exposed:
        method = 'post_delete'


    if hasattr(obj, method):
        possible_rest_method = getattr(obj, method)
        if hasattr(possible_rest_method, 'decoration') and possible_rest_method.decoration.exposed:

            if inspect.isclass(obj):
                obj = obj()
            #attach the parent class so the inner class has access to it's members
            obj.parent = parent
            obj = getattr(obj, method)
        else:
            raise HTTPNotFound().exception
    elif isinstance(obj, RestController):
        raise HTTPNotFound().exception

    return obj, remainder

def _find_object(obj, remainder, notfound_handlers):
    parent = None
    while True:
        if obj is None:
            raise HTTPNotFound().exception

        _check_controller_auth(obj)

        if _iscontroller(obj):
            return obj, parent, remainder

        if not remainder or (len(remainder) == 1 and remainder[0] == ''):
            if isinstance(remainder, tuple):
                remainder = list(remainder)
            index = getattr(obj, 'index', None)
            if _iscontroller(index):
                return index, obj, remainder

        default, lookup = _get_notfound_handlers(obj)

        if default:
            notfound_handlers.append(('default', default, obj, remainder))

        if lookup and remainder and not(len(remainder) == 1 and (remainder[0]=='')):
            notfound_handlers.append(('lookup', lookup, obj, remainder))

        #what causes this condition?
        if not remainder:
            raise HTTPNotFound().exception

        parent = obj

        try:
            obj = getattr(obj, remainder[0].encode("utf-8"), None)
            remainder = remainder[1:]
            # this can happen when parts of the path
            # contain non-ascii-characters.
            # If that's the case, we throw HTTPNotFound
            # and let a potential default-handler deal
            # with the issue
        except UnicodeEncodeError:
            raise HTTPNotFound().exception

def _get_notfound_handlers(obj):
    '''Return (default,lookup) notfound handlers for this object'''
    # First search for is_default and is_lookup decoration
    default = lookup = None
    for name in dir(obj):
        meth = getattr(obj, name)
        if hasattr(meth, 'decoration'):
            if not hasattr(meth.decoration, 'is_default_controller'):
                import pdb; pdb.set_trace()
            if meth.decoration.is_default_controller:
                default = meth
            elif meth.decoration.is_lookup_controller:
                lookup = meth
    if default is None:
        meth = getattr(obj, 'default', None)
        if meth and _iscontroller(meth):
            default = meth
    if lookup is None:
        meth = getattr(obj, 'lookup', None)
        if meth and _iscontroller(meth):
            lookup = meth
    return default, lookup

def _iscontroller(obj):
    if not hasattr(obj, '__call__'):
        return False
    if not hasattr(obj, 'decoration'):
        return False
    return obj.decoration.exposed

class RestController(DecoratedController):
    """A Decorated Controller that dispatches in a RESTful Manner.

    This controller was designed to follow Representational State Transfer protocol, also known as REST.
    The goal of this controller method is to provide the developer a way to map
    RESTful URLS to controller methods directly, while still allowing Normal Object Dispatch to occur.

    Here is a brief rundown of the methods which are called on dispatch along with an example URL.

    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | Method          | Description                                                  | Example Method(s) / URL(s)                 |
    +=================+==============================================================+============================================+
    | get_one         | Display one record.                                          | GET /movies/1                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | get_all         | Display all records in a resource.                           | GET /movies/                               |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | get             | A combo of get_one and get_all.                              | GET /movies/                               |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | GET /movies/1                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | new             | Display a page to prompt the User for resource creation.     | GET /movies/new                            |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | edit            | Display a page to prompt the User for resource modification. |  GET /movies/1/edit                        |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | post            | Create a new record.                                         | POST /movies/                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | put             | Update an existing record.                                   | POST /movies/1?_method=PUT                 |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | PUT /movies/1                              |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | post_delete     | Delete an existing record.                                   | POST /movies/1?_method=DELETE              |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | DELETE /movies/1                           |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | get_delete      | Display a delete Confirmation page.                          | GET /movies/1/delete                       |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | delete          | A combination of post_delete and get_delete.                 | GET /movies/delete                         |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | DELETE /movies/1                           |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | DELETE /movies/                            |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | POST /movies/1/delete                      |
    |                 |                                                              +--------------------------------------------+
    |                 |                                                              | POST /movies/delete                        |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+

    You may note the ?_method on some of the URLs.  This is basically a hack because exiting browsers
    do not support the PUT and DELETE methods.  Just note that if you decide to use a this resource with a web browser,
    you will likely have to add a _method as a hidden field in your forms for these items.  Also note that RestController differs
    from TGController in that it offers no index, default, or lookup.  It is intended primarily for  resource management.

    :References:

      `Controller <../main/Controllers.html>`_  A basic overview on how to write controller methods.

      `CrudRestController <../main/Extensions/Crud/index.html>`_  A way to integrate ToscaWdiget Functionality with RESTful Dispatch.

    """
    class decoration(object):
        """This is here so that the Object Dispatcher will recognize this class as an exposed controller."""
        exposed = True
        is_default_controller = is_lookup_controller = None

    @classmethod
    def _check_security(cls):
        if not hasattr(cls, "allow_only") or cls.allow_only is None:
            log.debug('No controller-wide authorization at %s', request.path)
            return True
        try:
            predicate = cls.allow_only
            predicate.check_authorization(request.environ)
        except NotAuthorizedError, e:
            reason = unicode(e)
            if hasattr(cls, '_failed_authorization'):
                # Should shortcircut the rest, but if not we will still
                # deny authorization
                cls._failed_authorization(reason)
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



class TGController(ObjectDispatchController):
    """
    TGController is a specialized form of ObjectDispatchController that forms the
    basis of standard TurboGears controllers.  The "Root" controller of a standard
    tg project must be a TGController.

    This controller can be used as a baseclass for anything in the
    object dispatch tree, but it MUST be used in the Root controller
    and any controller which you intend to do object dispatch from
    using Routes.

    This controller has a few reserved method names which provide special functionality.

    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | Method          | Description                                                  | Example URL(s)                             |
    +=================+==============================================================+============================================+
    | index           | The root of the controller.                                  | /                                          |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | default         | A method to call when all other methods have failed.         | /movies                                    |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+
    | lookup          | Allows the developer to return a                             | /location/23.35/2343.34/elevation          |
    |                 | Controller instance for further dispatch.                    |                                            |
    +-----------------+--------------------------------------------------------------+--------------------------------------------+


    :References:

      `Controller <../main/Controllers.html>`_  A basic overview on how to write controller methods.

    """

    def _perform_call(self, func, args):
        setup_i18n()
        routingArgs = None

        if isinstance(args, dict) and 'url' in args:
            routingArgs = args['url']

        try:
            controller, remainder, params = self._get_routing_info(routingArgs)
            # this has to be done before decorated controller is called because
            # otherwise the controller method will get sent, and the function name will
            # be lost.
            func_name = func.__name__
            if not args:
                args = []
            if func_name == '__before__' or func_name == '__after__':
                if func_name == '__before__' and hasattr(controller.im_class, '__before__'):
                    return controller.im_self.__before__(*args)
                if func_name == '__after__' and hasattr(controller.im_class, '__after__'):
                    return controller.im_self.__after__(*args)
                return
            result = DecoratedController._perform_call(
                self, controller, params, remainder=remainder)

        except HTTPException, httpe:
            result = httpe
            # 304 Not Modified's shouldn't have a content-type set
            if result.status_int == 304:
                result.headers.pop('Content-Type', None)
            result._exception = True
        return result

    def _check_security(self):
        if not hasattr(self, "allow_only") or self.allow_only is None:
            log.debug('No controller-wide authorization at %s', request.path)
            return True
        try:
            predicate = self.allow_only
            predicate.check_authorization(request.environ)
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


class WSGIAppController(TGController):
    """
    A controller you can use to mount a WSGI app.
    """
    def __init__(self, app, allow_only=None):
        self.app = app
        self.allow_only = allow_only
        # Signal tg.configuration.maybe_make_body_seekable which is wrapping
        # The stack to make the body seekable so default() can rewind it.
        config['make_body_seekable'] = True
        # Calling the parent's contructor, to enable controller-wide auth:
        super(WSGIAppController, self).__init__()

    @expose()
    def default(self, *args, **kw):
        """
        This method is called whenever a request reaches this controller.
        It prepares the WSGI environment and delegates the request to the
        WSGI app.
        """
        # Push into SCRIPT_NAME the path components that have been consumed,
        from pylons import request
        request = request._current_obj()
        new_req = request.copy()
        to_pop = len(new_req.path_info.strip('/').split('/')) - len(args)
        for i in xrange(to_pop):
            new_req.path_info_pop()
        if not new_req.path_info:
            # Append trailing slash and redirect
            redirect(request.path_info+'/')
        new_req.body_file.seek(0)
        return self.delegate(new_req.environ, request.start_response)

    def delegate(self, environ, start_response):
        """
        Delegates the request to the WSGI app.

        Override me if you need to update the environ, mangle response, etc...
        """
        return self.app(environ, start_response)


def url(*args, **kwargs):
    """Generate an absolute URL that's specific to this application.

    The URL function takes a string, appends the SCRIPT_NAME and adds url
    parameters for all of the other keyword arguments passed in.

    For backwards compatibility you can also pass in a params dictionary
    which is turned into url params, or you can send in a a list of
    strings as the first argument, which will be joined with /'s to
    make a url string.

    In general tg.url is just a proxy for pylons.url which is in turn
    a proxy for routes url_for function.  This means that if the first
    argument is not a basestring but a method that has been routed to,
    the standard routes url_for reverse lookup system will be used.
    """
    args = list(args)
    if isinstance(args[0], list):
        args[0] = u'/'.join(args[0])
    if args and isinstance(args[0], basestring):
        #First we handle the possibility that the user passed in params
        if isinstance(kwargs.get('params'), dict):
            params = kwargs['params'].copy()
            del kwargs['params']
            params.update(kwargs)
            kwargs = params

        if len(args) >= 2 and isinstance(args[1], dict):
            params = args[1].copy()
            if kwargs:
                params.update(kwargs)
            kwargs = params
            args.pop(1)

        if isinstance(args[0], unicode):
            args[0] = args[0].encode('utf8')
    return pylons_url(*args, **kwargs)

def redirect(*args, **kwargs):
    """Generate an HTTP redirect.

    The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the
    second request.
    """

    url(*args, **kwargs)
    found = HTTPFound(location=url(*args, **kwargs)).exception

    raise found

def use_wsgi_app(wsgi_app):
    return wsgi_app(request.environ, request.start_response)


# Idea stolen from Pylons
def pylons_formencode_gettext(value):
    from pylons.i18n import ugettext as pylons_gettext
    from gettext import NullTranslations

    trans = pylons_gettext(value)

    # Translation failed, try formencode
    if trans == value:

        try:
            fetrans = pylons.c.formencode_translation
        except AttributeError, attrerror:
            # the translator was not set in the Pylons context
            # we are certainly in the test framework
            # let's make sure won't return something that is ok with the caller
            fetrans = NullTranslations()

        if not fetrans:
            fetrans = NullTranslations()

        trans = fetrans.ugettext(value)

    return trans


__all__ = [
    "DecoratedController", "ObjectDispatchController", "TGController",
    "url", "redirect", "RestController"
    ]
