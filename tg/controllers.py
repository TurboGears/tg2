"""Basic controller classes for turbogears"""

import logging
import warnings
import urlparse, urllib

import formencode
import pylons
from pylons.controllers import WSGIController

from tg.exceptions import HTTPFound, HTTPNotFound, HTTPException
from toscawidgets.api import Widget

log = logging.getLogger(__name__)

log = logging.getLogger(__name__)

def _configured_engines():
    """Returns set with the currently configured template engine's names
    from the active application's globals"""
    g = pylons.app_globals._current_obj()
    if not hasattr(g, 'tg_configured_engines'):
        g.tg_configured_engines = set()
    return g.tg_configured_engines

class DecoratedController(WSGIController):

    def _perform_validate(self, controller, params):
        validation = getattr(controller.decoration, 'validation', None)
        if validation is None:
            return params
        
        #Provide a hook to do stuff before validation 
        if hasattr(validation, '_before_validate'):
            validation._before_validate(controller, params)
        
        #Initialize new_params -- if it never gets updated just return params
        new_params = None
        errors = {}
        
        #TG developers can pass in a dict of param names and validators
        #this applies them one by one and builds up a new set of validated params.
        if isinstance(validation.validators, dict):
            new_params = {}
            for field, validator in validation.validators.iteritems():
                try:
                    validator.to_python(params.get(field))
                    new_params[field] = validator.to_python(params.get(field))
                #catch individual validation errors    
                except formencode.api.Invalid, inv:
                    errors[field] = inv.msg
                    
            #re-raise a compound validation error, with the full error dict      
            if errors:
                raise formencode.api.Invalid(
                    formencode.schema.format_compound_error(errors),
                    params, None, error_dict=errors)
                    
            #Make sure unvalidated params get added back in
            for param, param_value in params.items():
                if not param in new_params:
                    new_params[param] = param_value
                
            
        elif isinstance(validation.validators, formencode.Schema):
            new_params = validation.validators.to_python(params)
        elif hasattr(validation.validators, 'validate'):
            #the object validates itself
            try:
                new_params = validation.validators.validate(params)
            except  formencode.api.Invalid, inv:
                error_list = inv.__str__().split('\n')
                #most invalids come back with a list of fields which 
                #are in error in the format: 
                #"fieldname1: error\nfieldname2: error"
                for error in error_list:
                    field_value = error.split(':')
                    #if the error has no field associated with it, 
                    #return the error as a global form error
                    if len(field_value) == 1:
                        errors['_the_form'] = field_value[0].strip()
                        continue
                    errors[field_value[0]] = field_value[1].strip()
                raise inv
        if new_params is None:
            return params
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
        if isinstance(response, dict):
            for key, item in response.iteritems():
                if isinstance(item, Widget):
                    msg = "Returning a widget is depricated, set them on pylons.w instead"
                    warnings.warn(msg, DeprecationWarning)
                    setattr(pylons.c.w, key, item)
        
        if engine_name not in _configured_engines():
            from pylons import config
            template_options = dict(config).get('buffet.template_options', {})
            pylons.buffet.prepare(engine_name, **template_options)
            _configured_engines().add(engine_name)

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
        pylons.c.form_errors = exception.error_dict
        pylons.c.form_values = exception.value

        error_handler = controller.decoration.validation.error_handler
        if error_handler is None:
            error_handler = controller

        output = error_handler(**dict(params))

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
            url_path = pylons.request.path.split('/')[1:]
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
        controller, remainder, params = self._get_routing_info(args.get('url'))
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
        except HTTPException:
            if not notfound_handlers:
                raise HTTPNotFound().exception
            name, obj, remainder = notfound_handlers.pop()
            if name == 'default':
                return obj, remainder
            else:
                obj, remainder = obj(*remainder)
                continue


def find_object(obj, remainder, notfound_handlers):
    while True:
        if obj is None:
            raise HTTPNotFound().exception
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
            raise HTTPNotFound().exception
        obj = getattr(obj, remainder[0], None)
        remainder = remainder[1:]


def iscontroller(obj):
    if not hasattr(obj, '__call__'):
        return False
    if not hasattr(obj, 'decoration'):
        return False
    return obj.decoration.exposed

class TGController(ObjectDispatchController):
    """Basis TurboGears controller class which is derived from
    pylons ObjectDispatchController
    
    This controller can be used as a baseclass for anything in the 
    object dispatch tree, but it MUST be used in the Root controller
    ad any controller which you intend to do object dispatch from
    using Routes."""
    
    def _perform_call(self, func, args):
        setup_i18n()
        self._initialize_validation_context()
        routingArgs = None
        
        #TODO: Why do this, rather than always using the 
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
    """Generate an HTTP redirect. The function raises an exception internally,
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
    """Broken url() re-implementation from TG1.
    See #1649 for more info.
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

