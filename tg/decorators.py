# -*- coding: utf-8 -*-
"""
Decorators use by the TurboGears controllers.

Not all of these decorators are traditional wrappers. They are much simplified
from the turbogears 1 decorators, because all they do is register attributes on
the functions they wrap, and then the DecoratedController provides the hooks
needed to support these decorators.

"""
import inspect
import formencode
from paste.util.mimeparse import best_match
from decorator import decorator

#this can be removed after tg_format is removed
import mimetypes
import warnings

from webob.exc import HTTPUnauthorized
from webob.multidict import MultiDict
from webhelpers.paginate import Page
from pylons import config, request, response
from pylons.controllers.util import abort
from pylons import tmpl_context as c
from tg.util import partial
from repoze.what.plugins.pylonshq import ActionProtector, ControllerProtector

from tg.configuration import Bunch
from tg.flash import flash
#from tg.controllers import redirect

class Decoration(object):
    """ Simple class to support 'simple registration' type decorators
    """
    def __init__(self, controller):
        self.controller = controller
        self.engines = {}
        self.custom_engines = {}
        self.render_custom_format = None
        self.validation = None
        self.error_handler = None
        self.is_default_controller = False
        self.is_lookup_controller = False
        self.hooks = dict(before_validate=[],
                          before_call=[],
                          before_render=[],
                          after_render=[])

    def get_decoration(cls, func):
        if not hasattr(func, 'decoration'):
            func.decoration = cls(func)
        return func.decoration
    get_decoration = classmethod(get_decoration)

    def exposed(self):
        return bool(self.engines)
    exposed = property(exposed)

    def run_hooks(self, hook, *l, **kw):
        for func in self.hooks[hook]:
            func(*l, **kw)

    def register_template_engine(self, content_type, engine, template,
                                 exclude_names):
        """Registers an engine on the controller.

        Multiple engines can be registered, but only one engine per
        content_type.  If no content type is specified the engine is
        registered at */* which is the default, and will be used
        whenever no content type is specified.

        exclude_names keeps track of a list of keys which will be
        removed from the controller's dictionary before it is loaded
        into the template.  This allows you to exclude some information
        from JSONification, and other 'automatic' engines which don't
        require a template.
        """

        if content_type is None:
            content_type = '*/*'
        self.engines[content_type] = engine, template, exclude_names

    def register_custom_template_engine(self, custom_format, content_type, engine, template,
                                        exclude_names):
        """Registers a custom engine on the controller.

        Mulitple engines can be registered, but only one engine per
        custom_format.

        The engine is registered when @expose is used with the
        custom_format parameter and controllers render using this
        engine when the use_custom_format() function is called
        with the corresponding custom_format.

        exclude_names keeps track of a list of keys which will be
        removed from the controller's dictionary before it is loaded
        into the template.  This allows you to exclude some information
        from JSONification, and other 'automatic' engines which don't
        require a template.
        """

        if content_type is None:
            content_type = "*/*"
        self.custom_engines[custom_format] = content_type, engine, template, exclude_names

    def lookup_template_engine(self, request):
        """Return the template engine data.

        Provides a convenience method to get the proper engine,
        content_type, template, and exclude_names for a particular
        tg_format (which is pulled off of the request headers).
        """
        #remove this after deprecation period for tg_format
        tg_format = request.headers.get('tg_format')

        if hasattr(request, 'response_type') and request.response_type in self.engines:
            accept_types = request.response_type

        elif tg_format:
            warnings.warn('tg_format is now deprecated.  Use .mimetype in your URL to create the same behavior')
            if '/' not in tg_format:
                accept_types = mimetypes.guess_type('.'+tg_format)[0]
                if accept_types is None:
                    raise Exception('Unknown mimetype: %s'%tg_format)
            else:
                accept_types = tg_format
        else:
            accept_types = request.headers.get('accept', '*/*')

        if self.render_custom_format:
            content_type, engine, template, exclude_names = self.custom_engines[self.render_custom_format]

        else:
            content_type = best_match(self.engines.keys(), accept_types)
            # check for overridden templates
            try:
                engine, template, exclude_names = request._override_mapping[self.controller][content_type]
            except (AttributeError, KeyError):
                engine, template, exclude_names = self.engines[content_type]


        if 'charset' not in content_type and (
           content_type.startswith('text') or content_type  == 'application/json'):
            content_type = '%s; charset=utf-8' % content_type

        return content_type, engine, template, exclude_names

    def register_hook(self, hook_name, func):
        """Registers the specified function as a hook.

        We now have four core hooks that can be applied by adding
        decorators: before_validate, before_call, before_render, and
        after_render. register_hook attaches the function to the hook
        which get's called at the apropriate time in the request life
        cycle.)
        """
        self.hooks[hook_name].append(func)


class _hook_decorator(object):
    """SuperClass for all the specific TG2 hook validators.
    """
    # must be overridden by a particular hook
    hook_name = None

    def __init__(self, hook_func):
        self.hook_func = hook_func

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco.register_hook(self.hook_name, self.hook_func)
        return func


class before_validate(_hook_decorator):
    """A list of callables to be run before validation is performed"""
    hook_name = 'before_validate'


class before_call(_hook_decorator):
    """A list of callables to be run before the controller method is called"""
    hook_name = 'before_call'


class before_render(_hook_decorator):
    """A list of callables to be run before the template is rendered"""
    hook_name = 'before_render'


class after_render(_hook_decorator):
    """A list of callables to be run after the template is rendered.

    Will be run before it is returned returned up the WSGI stack"""

    hook_name = 'after_render'


class expose(object):
    """
    Registers attributes on the decorated function

    :Parameters:
      template
        Assign a template, you could use the syntax 'genshi:template'
        to use different templates.
        The default template engine is genshi.
      content_type
        Assign content type.
        The default content type is 'text/html'.
      exclude_names
        Assign exclude names

    The expose decorator registers a number of attributes on the
    decorated function, but does not actually wrap the function the way
    TurboGears 1.0 style expose decorators did.

    This means that we don't have to play any kind of special tricks to
    maintain the signature of the exposed function.

    The exclude_names parameter is new, and it takes a list of keys that
    ought to be scrubbed from the dictinary before passing it on to the
    rendering engine.  This is particularly usefull for JSON.

    Expose decorator can be stacked like this::

        @expose('json', exclude_names='d')
        @expose('kid:blogtutorial.templates.test_form',
                content_type='text/html')
        @expose('kid:blogtutorial.templates.test_form_xml',
                content_type='text/xml', custom_format='special_xml')
        def my_exposed_method(self):
            return dict(a=1, b=2, d="username")

    The expose('json') syntax is a special case.  json is a buffet
    rendering engine, but unlike others it does not require a template,
    and expose assumes that it matches content_type='application/json'

    If you want to declare a desired content_type in a url, you
    can use the mime-type style dotted notation::

        "/mypage.json" ==> for json
        "/mypage.html" ==> for text/html
        "/mypage.xml" ==> for xml.

    If you're doing an http post, you can also declare the desired
    content type in the accept headers, with standard content type
    strings.

    By default expose assumes that the template is for html.  All other
    content_types must be explicitly matched to a template and engine.

    The last expose uses the custom_format parameter which takes an
    arbitrary value (in this case 'special_xml').  You can then use
    the`use_custom_format` function within the method to decide which
    of the 'custom_format' registered expose decorators to use to
    render the template.
    """

    def __init__(self, template='', content_type=None, exclude_names=None,
                 custom_format=None):
        if exclude_names is None:
            exclude_names = []

        if template == 'json':
            engine, template = 'json', ''

        elif ':' in template:
            engine, template = template.split(':', 1)

        elif template:
            # Use the default templating engine from the config
            if config.get('use_legacy_renderer'):
                engine = config['buffet.template_engines'][0]['engine']

            else:
                engine = config.get('default_renderer')

        else:
            engine, template = None, None

        if content_type is None:
            if engine == 'json':
                content_type = 'application/json'
            else:
                content_type = 'text/html'

        if engine == 'json' and 'tmpl_context' not in exclude_names:
            exclude_names.append('tmpl_context')

        self.engine = engine
        self.template = template
        self.content_type = content_type
        self.exclude_names = exclude_names
        self.custom_format = custom_format

    def __call__(self, func):
        deco = Decoration.get_decoration(func)

        if self.custom_format:
            deco.register_custom_template_engine(
                self.custom_format, self.content_type, self.engine,
                self.template, self.exclude_names)
        else:
            deco.register_template_engine(
                self.content_type, self.engine, self.template, self.exclude_names)
        return func

def use_custom_format(controller, custom_format):
    """Use use_custom_format in a controller in order to change
    the active @expose decorator when available."""
    deco = Decoration.get_decoration(controller)

    # Check the custom_format passed is available for use
    if not custom_format in deco.custom_engines.keys():
        raise ValueError("'%s' is not a valid custom_format" % custom_format)

    deco.render_custom_format = custom_format

def override_template(controller, template):
    """Use overide_template in a controller in order to change the
    template that will be used to render the response dictionary
    dynamically.

    The template string passed in requires that
    you include the template engine name, even if you're using the default.

    So you have to pass in a template id string like::

       "genshi:myproject.templates.index2"

    future versions may make the `genshi:` optional if you want to use
    the default engine.
    """
    if hasattr(controller, 'decoration'):
        decoration = controller.decoration
    else:
        return
    if hasattr(decoration, 'engines'):
        engines = decoration.engines
    else:
        return

    text_engine = engines.get('text/html')
    template = template.split(':')
    template.extend(text_engine[2:])
    try:
        override_mapping = request._override_mapping
    except AttributeError:
        override_mapping = request._override_mapping = {}
    override_mapping[controller.im_func] = {"text/html" : template}


class validate(object):
    """Regesters which validators ought to be applied

    If you want to validate the contents of your form,
    you can use the ``@validate()`` decorator to regester
    the validators that ought to be called.

    :Parameters:
      validators
        Pass in a dictionary of FormEncode validators.
        The keys should match the form field names.
      error_handler
        Pass in the controller method which shoudl be used
        to handle any form errors
      form
        Pass in a ToscaWidget based form with validators

    The first positional parameter can either be a dictonary of validators,
    a FormEncode schema validator, or a callable which acts like a FormEncode
    validator.

    """
    def __init__(self, validators=None, error_handler=None, form=None):
        if form:
            self.validators = form
        if validators:
            self.validators = validators
        self.error_handler = error_handler

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco.validation = self
        return func

def default(func):
    '''Registers a method as the "default" controller method'''
    deco = Decoration.get_decoration(func)
    deco.is_default_controller = True
    return func
        
def lookup(func):
    '''Registers a method as the "lookup" controller method'''
    deco = Decoration.get_decoration(func)
    deco.is_lookup_controller = True
    return func

def paginate(name, items_per_page=10, use_prefix=False):
    """
    Paginate a given collection.

    This decorator is mainly exposing the functionality
    of :func:`webhelpers.paginate`.

    :Usage:

    You use this decorator as follows::

     class MyController(object):

         @expose()
         @paginate("collection")
         def sample(self, *args):
             collection = get_a_collection()
             return dict(collection=collection)

    To render the actual pager, use::

      ${c.paginators.<name>.pager()}

    where c is the tmpl_context.

    It is possible to have several :func:`paginate`-decorators for
    one controller action to paginate several collections independently
    from each other. If this is desired, don't forget to set the :attr:`use_prefix`-parameter
    to :const:`True`.

    :Parameters:
      name
        the collection to be paginated.
      items_per_page
        the number of items to be rendered. Defaults to 10
      use_prefix
        if True, the parameters the paginate
        decorator renders and reacts to are prefixed with
        "<name>_". This allows for multi-pagination.

    """
    prefix = ""
    if use_prefix:
        prefix = name + "_"
    own_parameters = dict(
        page="%spage" % prefix,
        items_per_page="%sitems_per_page" % prefix
        )
    #@decorator
    def _d(f):
        def _w(*args, **kwargs):
            page = int(kwargs.pop(own_parameters["page"], 1))
            real_items_per_page = int(
                    kwargs.pop(
                            own_parameters['items_per_page'],
                            items_per_page))
            argvars = inspect.getargspec(f)[0][1:]
            if argvars:
                args = list(args)
                for i, var in enumerate(args):
                    if i>=len(argvars):
                        break;
                    var = argvars[i]
                    if var in kwargs:
                        args[i] = kwargs[var]
                        del kwargs[var]
            
            res = f(*args, **kwargs)
            if isinstance(res, dict) and name in res:
                additional_parameters = MultiDict()
                for key, value in request.str_params.iteritems():
                    if key not in own_parameters:
                        additional_parameters.add(key, value)

                collection = res[name]
                page = Page(
                    collection,
                    page,
                    items_per_page=real_items_per_page,
                    **additional_parameters.dict_of_lists()
                    )
                # wrap the pager so that it will render
                # the proper page-parameter
                page.pager = partial(page.pager,
                        page_param=own_parameters["page"])
                res[name] = page
                # this is a bit strange - it appears
                # as if c returns an empty
                # string for everything it dosen't know.
                # I didn't find that documented, so I
                # just put this in here and hope it works.
                if not hasattr(c, 'paginators') or type(c.paginators) == str:
                    c.paginators = Bunch()
                c.paginators[name] = page
            return res
        return _w
    return _d

@decorator
def postpone_commits(func, *args, **kwargs):
    """Turns sqlalchemy commits into flushes in the decorated method

    This has the end-result of postponing the commit to the normal TG2
    transaction boundry. """

    #TODO: Test and document this.
    s = config.get('DBSession', None)
    assert hasattr(s, 'commit')
    old_commit = s.commit
    s.commit = s.flush
    retval = func(*args, **kwargs)
    s.commit = old_commit
    return retval

@decorator
def without_trailing_slash(func, *args, **kwargs):
    """This decorator allows you to ensure that the URL does not end in "/"
    The decorator accomplish this by redirecting to the correct URL.

    :Usage:

    You use this decorator as follows::

     class MyController(object):

         @without_trailing_slash
         @expose()
         def sample(self, *args):
             return "found sample"

    In the above example http://localhost:8080/sample/ redirects to http://localhost:8080/sample
    In addition, the URL http://localhost:8080/sample/1/ redirects to http://localhost:8080/sample/1
    """
    if request.method == 'GET' and request.path.endswith('/') and not(request.response_type) and len(request.params)==0:
        from tg.controllers import redirect
        redirect(request.url[:-1])
    return func(*args, **kwargs)

@decorator
def with_trailing_slash(func, *args, **kwargs):
    """This decorator allows you to ensure that the URL ends in "/"
    The decorator accomplish this by redirecting to the correct URL.

    :Usage:

    You use this decorator as follows::

     class MyController(object):

         @with_trailing_slash
         @expose()
         def sample(self, *args):
             return "found sample"

    In the above example http://localhost:8080/sample redirects to http://localhost:8080/sample/
    In addition, the URL http://localhost:8080/sample/1 redirects to http://localhost:8080/sample/1/
    """
    if request.method == 'GET' and not(request.path.endswith('/')) and not(request.response_type) and len(request.params)==0:
        from tg.controllers import redirect
        redirect(request.url+'/')
    return func(*args, **kwargs)

#{ Authorization decorators


class require(ActionProtector):
    """
    TurboGears-specific repoze.what-pylons action protector.
    
    The default authorization denial handler of this protector will flash
    the message of the unmet predicate with ``warning`` or ``error`` as the
    flash status if the HTTP status code is 401 or 403, respectively.
    
    See :class:`allow_only` for controller-wide authorization.
    
    """
    
    def default_denial_handler(self, reason):
        """Authorization denial handler for repoze.what-pylons protectors."""
        if response.status_int == 401:
            status = 'warning'
        else:
            # Status is a 403
            status = 'error'
        flash(reason, status=status)
        abort(response.status_int, reason)


class allow_only(ControllerProtector):
    """
    TurboGears-specific repoze.what-pylons controller protector.
    
    The default authorization denial handler of this protector will flash
    the message of the unmet predicate with ``warning`` or ``error`` as the
    flash status if the HTTP status code is 401 or 403, respectively, since
    by default the ``__before__`` method of the controller is decorated with
    :class:`require`.
    
    If the controller class has the ``_failed_authorization`` *class method*,
    it will replace the default denial handler.
    
    """
    protector = require
    
    def __call__(self, cls, *args, **kwargs):
        if hasattr(cls, '_failed_authorization'):
            self.denial_handler = cls._failed_authorization
        return super(allow_only, self).__call__(cls, *args, **kwargs)


#}
