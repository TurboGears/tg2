# -*- coding: utf-8 -*-
"""
Basic controller classes for turbogears

  DecoratedController allows the decorators in tg.decorators to work

  ObjectDispatchController is a specialised form of DecoratedController that
  converts URL portions into traversing Python objects.  This controller is
  usable in plain pylons if you route to it's "routes_placeholder" method

  TGController is a specialised form of ObjectDispatchController that forms the
  basis of standard TurboGears controllers.  The "Root" controller of a standard
  tg project must be a TGController.
"""

import logging
import warnings
import urlparse, urllib
import mimetypes
import inspect

import formencode
import pylons
from pylons import url as pylons_url
from pylons.controllers import WSGIController
import tw
from repoze.what.authorize import check_authorization, NotAuthorizedError

from tg.exceptions import (HTTPFound, HTTPNotFound, HTTPException,
    HTTPClientError)
from tg.render import render as tg_render
from tg.decorators import expose
from tg.flash import flash

from webob import Request
from webob.exc import HTTPUnauthorized

log = logging.getLogger(__name__)

# If someone goes @expose(content_type=CUSTOM_CONTENT_TYPE) then we won't
# override pylons.request.content_type
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
        pylons.request.start_response = self.start_response

        if remainder is None:
            remainder = []
        try:
            pylons.request.headers['tg_format'] = params.get('tg_format', None)

            controller.decoration.run_hooks('before_validate', remainder,
                                            params)

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

        #import pdb; pdb.set_trace()
        if validation is None:
            return params

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
                    validator.to_python(params.get(field))
                    new_params[field] = validator.to_python(params.get(field))
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
            new_params = validation.validators.to_python(params)

        elif hasattr(validation.validators, 'validate') and hasattr(validation, 'needs_controller') and validation.needs_controller:
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(controller, params)

        elif hasattr(validation.validators, 'validate'):
            # An object with a "validate" method - call it with the parameters
            new_params = validation.validators.validate(params)

        # Theoretically this should not happen...
        if new_params is None:
            return params

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
            controller.decoration.lookup_template_engine(pylons.request)

        if content_type != CUSTOM_CONTENT_TYPE:
            pylons.response.headers['Content-Type'] = content_type

        #skip all the complicated stuff if we're just passing a string along.
        if isinstance(response, basestring):
            return response

        # Save these objeccts as locals from the SOP to avoid expensive lookups
        req = pylons.request._current_obj()
        tmpl_context = pylons.tmpl_context._current_obj()
        use_legacy_renderer = pylons.config.get("use_legacy_renderer", True)

        if template_name is None:
            return response

        # Prepare the engine, if it's not already been prepared.
        # json is a buffet engine ATM
        if use_legacy_renderer or 'json' == engine_name:
            # get the buffet handler
            buffet = pylons.buffet._current_obj()

            if engine_name not in _configured_engines():
                from pylons import config
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
            url_path = pylons.request.path.split('/')[1:]
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
        return controller, remainder, pylons.request.params.mixed()

    def _perform_call(self, func, args):
        controller, remainder, params = self._get_routing_info(args.get('url'))
        return DecoratedController._perform_call(
            self, controller, params, remainder=remainder)

    def routes_placeholder(self, url='/', start_response=None, **kwargs):
        """
        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.
        """
        pass


def _object_dispatch(obj, url_path):
    remainder = url_path

    pylons.request.response_type = None
    # if the last item in the remainder has an extention
    # remove the extension, and add a content type to the request
    # parameters
    if remainder and '.' in remainder[-1]:
        last_remainder = remainder[-1]
        extension_spot = last_remainder.rfind('.')
        extension = last_remainder[extension_spot-1:]
        remainder[-1] = last_remainder[:extension_spot]
        pylons.request.response_type = mimetypes.guess_type(extension)[0]
        pylons.request.response_ext = extension
        
    notfound_handlers = []
    while True:
        try:
            obj, parent, remainder = _find_object(obj, remainder, notfound_handlers)

            return _find_restful_dispatch(obj, parent, remainder)

        # auth error should be treated separatly from "not found" errors
        except HTTPUnauthorized, httpe:
            log.debug("a 401 error occured for obj: %s" % obj)
            raise

        except HTTPException:
            if not notfound_handlers:
                raise HTTPNotFound().exception

            name, obj, parent, remainder = notfound_handlers.pop()
            if name == 'default':
                return _find_restful_dispatch(obj, parent, remainder)

            else:
                print 'in not found handlers'
                obj, remainder = obj(*remainder)
                list(remainder)
                continue

def _find_restful_dispatch(obj, parent, remainder):

    _check_security(obj)

    if not inspect.isclass(obj) and not isinstance(obj, RestController):
        return obj, remainder
    if inspect.isclass(obj) and not issubclass(obj, RestController):
        return obj, remainder

    request_method = method = pylons.request.method.lower()
    
    #conventional hack for handling methods which are not supported by most browsers
    params = pylons.request.params
    if '_method' in params:
        if params['_method']:
            method = params['_method'].lower()

    if remainder and remainder[-1] == '':
            remainder = remainder[:-1]
    if remainder:
        #dispatch is finished, and we are where we need to be
        if remainder[-1] in ['new', 'edit'] and len(remainder)<=2:
            if method == 'get':
                method = remainder[-1]
            if method == 'edit' and len(remainder) <=2:
                remainder = remainder[:-1]
            if method == 'new' and len(remainder) == 1:
                remainder = remainder[:-1]
        elif remainder[-1] == 'delete' and len(remainder)<=2:
            method = 'delete'
            if len(remainder) <= 2:
                remainder = remainder[:-1]
        if remainder and hasattr(obj, remainder[0]) and remainder[0] not in ['new', 'edit']:
            #revert the dispatch back to object_dispatch
            if inspect.isclass(obj):
                obj = obj()
            return _find_restful_dispatch(*_find_object(getattr(obj, remainder[0]), remainder[1:], []))

    #support for get_all and get_one methods
    if not remainder and method == 'get' and hasattr(obj, 'get_all') and obj.get_all.decoration.exposed:
        method = 'get_all'
    if len(remainder)>0 and method == 'get' and hasattr(obj, 'get_one') and obj.get_one.decoration.exposed:
        if len(remainder) == 1:
            method = 'get_one'
        else:
            func = getattr(obj, 'get_one')
            arg_len = len(inspect.getargspec(func)[0])-1
            remainder = remainder[arg_len:]
            if len(remainder) > 0 and hasattr(obj, remainder[0]):
                return _find_restful_dispatch(*_find_object(getattr(obj, remainder[0]), remainder[1:], []))
            else:
                raise HTTPNotFound().exception

    #support for get_delete and post_delete methods
    if request_method == 'get' and method == 'delete' and hasattr(obj, 'get_delete') and obj.get_delete.decoration.exposed:
        method = 'get_delete'
    if request_method == 'post' and method == 'delete' and hasattr(obj, 'post_delete') and obj.post_delete.decoration.exposed:
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

        _check_security(obj)

        if _iscontroller(obj):
            return obj, parent, remainder
        
        if not remainder or (len(remainder) == 1 and remainder[0] == ''):
            if isinstance(remainder, tuple):
                remainder = list(remainder)
            index = getattr(obj, 'index', None)
            if _iscontroller(index):
                return index, obj, remainder

        default = getattr(obj, 'default', None)
        if _iscontroller(default):
            notfound_handlers.append(('default', default, obj, remainder))

        lookup = getattr(obj, 'lookup', None)
        if remainder and not(len(remainder) == 1 and (remainder[0]=='')) and _iscontroller(lookup):
            notfound_handlers.append(('lookup', lookup, obj, remainder))

        if not remainder:
            raise HTTPNotFound().exception

        parent = obj
        obj = getattr(obj, remainder[0], None)
        remainder = remainder[1:]

def _check_security(obj):
    """this function checks if a controller has a 'require' attribute and if
    it is the case, test that this require predicate can be evaled to True.
    It will raise a Forbidden exception if the predicate is not valid.
    """
    if hasattr(obj, "im_self"):
        klass_instance = obj.im_self
    else:
        klass_instance = obj

    if hasattr(klass_instance, "_check_security"):
        if not klass_instance._check_security():
            raise HTTPUnauthorized().exception

def _iscontroller(obj):
    if not hasattr(obj, '__call__'):
        return False
    if not hasattr(obj, 'decoration'):
        return False
    return obj.decoration.exposed

class RestController(DecoratedController):
    """This Dummies out a controller so that restfullness can take place"""
    class decoration(object):
        exposed = True

class TGController(ObjectDispatchController):
    """
    An ObjectDispatchController-derived class for stock-standard TurboGears
    controllers.

    This controller can be used as a baseclass for anything in the
    object dispatch tree, but it MUST be used in the Root controller
    and any controller which you intend to do object dispatch from
    using Routes.
    """

    def _perform_call(self, func, args):
        setup_i18n()
        routingArgs = None

        if isinstance(args, dict) and 'url' in args:
            routingArgs = args['url']

        try:
            controller, remainder, params = self._get_routing_info(routingArgs)
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
        if not hasattr(self, "allow_only") or  self.allow_only is None:
            log.debug('No controller authorization at %s',
                      pylons.request.path)
            return True
        
        environ = pylons.request.environ
        try:
            check_authorization(self.allow_only, environ)
            log.debug('Succeeded controller-wide authorization at %s',
                      pylons.request.path)
            return True
        except NotAuthorizedError, error:
            log.debug('Failed controller authorization at %s', 
                      pylons.request.path)
            flash(unicode(error), status="status_warning")
            return False

class WSGIAppController(TGController):
    """
    A controller you can use to mount a WSGI app.
    """
    def __init__(self, app, allow_only=None):
        self.app = app
        self.allow_only = allow_only
        # Signal tg.configuration.maybe_make_body_seekable which is wrapping
        # The stack to make the body seekable so default() can rewind it.
        pylons.config['make_body_seekable'] = True

    @expose()
    def default(self, *args, **kw):
        """
        This method is called whenever a request reaches this controller.
        It prepares the WSGI environment and delegates the request to the
        WSGI app.
        """
        # Push into SCRIPT_NAME the path components that have been consumed,
        request = pylons.request._current_obj()
        new_req = request.copy()
        to_pop = len(new_req.path_info.strip('/').split('/')) - len(args)
        for i in xrange(to_pop):
            new_req.path_info_pop()
        if not new_req.path_info:
            # Append trailing slash and redirect
            redirect(request.script_name+request.path_info+'/')
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

    For backwards compatability you can also pass in a params dictionary
    which is turned into url params.

    In general tg.url is just a proxy for pylons.url which is in turn
    a proxy for routes url_for function.  But if tg1 like params are
    passed in we support a params dictionary in additon to the standard
    keyword arguments.
    """
    args = list(args)
    if args and isinstance(args[0], basestring):
        #First we handle the possibility that the user passed in params
        if isinstance(kwargs.get('params'), dict):
            params = kwargs['params'].copy()
            del kwargs['params']
#            print "kwargs:", kwargs
            params.update(kwargs)
#            print "updated params:", params
            kwargs = params
#            print "final kwargs:", kwargs

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
    browser; if the request is POST, the browser will issue GET for the second
    request.
    """

    url(*args, **kwargs)
    found = HTTPFound(location=url(*args, **kwargs)).exception

    raise found

def use_wsgi_app(wsgi_app):
    return wsgi_app(pylons.request.environ, pylons.request.start_response)


def setup_i18n():
    from pylons.i18n import add_fallback, set_lang, LanguageError
    languages = pylons.request.accept_language.best_matches()

    if languages:
        # get a copy of the languages list because we will
        # edit languages and cannot iter directly on it.
        for lang in languages[:]:
            try:
                add_fallback(lang)
            except LanguageError:
                # if there is no resource bundle for this language
                # remove the language from the list
                languages.remove(lang)
                log.debug("Skip language %s: not supported", lang)

        # if any language is left, set the best match as a default
        if languages:
            set_lang(languages[0])
            log.info("Set request language to %s", languages[0])

__all__ = [
    "DecoratedController", "ObjectDispatchController", "TGController",
    "url", "redirect", "RestController"
    ]
