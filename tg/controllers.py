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

import formencode
import pylons
from pylons.controllers import WSGIController

from pylons.controllers.util import abort

from tg.exceptions import HTTPFound, HTTPNotFound, HTTPException
from tw.api import Widget

log = logging.getLogger(__name__)

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
        be FormEncode Invalid objets.
        """

        validation = getattr(controller.decoration, 'validation', None)
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

        # Always set content type
        pylons.response.headers['Content-Type'] = content_type 
        req = pylons.request

        if template_name is None:
            return response

        # Deprecation warnings if people return a widget in the dict rather
        # than setting it on tmpl_context.w
        if isinstance(response, dict):
            for key, item in response.iteritems():
                if isinstance(item, Widget):
                    msg = "Returning a widget is deprecated, set them on pylons.widgets instead"
                    warnings.warn(msg, DeprecationWarning)
                    setattr(pylons.c.w, key, item)
        
        # Prepare the engine, if it's not already been prepared.
        if engine_name not in _configured_engines():
            from pylons import config
            template_options = dict(config).get('buffet.template_options', {})
            pylons.buffet.prepare(engine_name, **template_options)
            _configured_engines().add(engine_name)

        #if there is an identity, push it to the pylons template context
        pylons.tmpl_context.identity = pylons.request.environ.get('repoze.who.identity')
            
        # Setup the template namespace, removing anything that the user
        # has marked to be excluded.
        namespace = dict(tmpl_context=pylons.tmpl_context)
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
        return controller, remainder, pylons.request.params

    def _perform_call(self, func, args):
        controller, remainder, params = self._get_routing_info(args.get('url'))
        return DecoratedController._perform_call(self, controller, params,
                                                 remainder=remainder)

    def routes_placeholder(self, url='/', start_response=None, **kwargs):        
        """
        This function does not do anything.  It is a placeholder that allows
        Routes to accept this controller as a target for its routing.
        """
        pass


def _object_dispatch(obj, url_path):
    remainder = url_path

    notfound_handlers = []
    while True:
        try:
            obj, remainder = _find_object(obj, remainder, notfound_handlers)
            return obj, remainder
        except HTTPException:
            if not notfound_handlers:
                raise HTTPNotFound().exception
            name, obj, remainder = notfound_handlers.pop()
            if name == 'default':
                return obj, remainder
            else:
                obj, remainder = obj(*remainder)
                continue

def _find_object(obj, remainder, notfound_handlers):
    while True:
        if obj is None:
            raise HTTPNotFound().exception
        if _iscontroller(obj):
            return obj, remainder

        if not remainder or remainder == ['']:
            index = getattr(obj, 'index', None)
            if _iscontroller(index):
                return index, remainder

        default = getattr(obj, 'default', None)
        if _iscontroller(default):
            notfound_handlers.append(('default', default, remainder))

        lookup = getattr(obj, 'lookup', None)
        if _iscontroller(lookup):
            notfound_handlers.append(('lookup', lookup, remainder))

        if not remainder:
            raise HTTPNotFound().exception
        obj = getattr(obj, remainder[0], None)
        remainder = remainder[1:]

def _iscontroller(obj):
    if not hasattr(obj, '__call__'):
        return False
    if not hasattr(obj, 'decoration'):
        return False
    return obj.decoration.exposed

class TGController(ObjectDispatchController):
    """
    An ObjectDispatchController-derived class for stock-standard TurboGears
    controllers.
    
    This controller can be used as a baseclass for anything in the 
    object dispatch tree, but it MUST be used in the Root controller
    ad any controller which you intend to do object dispatch from
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

def redirect(url, params=None, **kw):
    """
    Generate an HTTP redirect. The function raises an exception internally,
    which is handled by the framework. The URL may be either absolute (e.g.
    http://example.com or /myfile.html) or relative. Relative URLs are
    automatically converted to absolute URLs. Parameters may be specified,
    which are appended to the URL. This causes an external redirect via the
    browser; if the request is POST, the browser will issue GET for the second
    request.
    """
    if not params:
        params = {}
    
    curent_url = pylons.request.url
    url = urlparse.urljoin(curent_url, url)
    params.update(kw)
    if params:
        url += (('?' in url) and '&' or '?') + urllib.urlencode(params, True)
    if isinstance(url, unicode):
        url = url.encode('utf8')
    found = HTTPFound(location=url).exception
    
    #TODO: Make this work with WebOb
    
    ## Merging cookies and headers from global response into redirect
    #for header in pylons.response.headerlist:
        #if header[0] == 'Set-Cookie' or header[0].startswith('X-'):
            #found.headers.append(header)
    raise found

def url(tgpath, tgparams=None, **kw):
    """
    url() re-implementation from TG1
    """

    if not isinstance(tgpath, basestring):
        tgpath = "/".join(list(tgpath))
    if tgpath.startswith("/"):
        app_root = pylons.request.application_url[len(pylons.request.host_url):]
        tgpath = app_root + tgpath
        tgpath = pylons.config.get("server.webpath", "") + tgpath 
        result = tgpath
    else:
        result = tgpath 

    if tgparams is None:
        tgparams = kw
    else:
        try:
            tgparams = tgparams.copy()
            tgparams.update(kw)
        except AttributeError:
            raise TypeError('url() expects a dictionary for query parameters')
    args = []
    for key, value in tgparams.iteritems():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            pairs = [(key, v) for v in value]
        else:
            pairs = [(key, value)]
        for (k, v) in pairs:
            if v is None:
                continue
            if isinstance(v, unicode):
                v = v.encode("utf8")
            args.append("%s=%s" % (k, urllib.quote(str(v))))
    if args:
        result += "?" + "&".join(args)
    return result
    

def setup_i18n():
    from pylons.i18n import add_fallback, set_lang, LanguageError
    languages = pylons.request.accept_language.best_matches()
    if languages:
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
    "url", "redirect"
    ]
