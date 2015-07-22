# -*- coding: utf-8 -*-
"""
Decorators use by the TurboGears controllers.

Not all of these decorators are traditional wrappers. They are much simplified
from the TurboGears 1 decorators, because all they do is register attributes on
the functions they wrap, and then the DecoratedController provides the hooks
needed to support these decorators.

"""
import copy
import warnings
import time
from functools import partial
from .exceptions import HTTPUnauthorized, HTTPMethodNotAllowed, HTTPMovedPermanently
from tg.support import NoDefault
from tg.support.paginate import Page
from tg.configuration import config
from tg.configuration.app_config import _DeprecatedControllerWrapper, call_controller
from tg.controllers.util import abort, redirect
from tg import tmpl_context, request, response
from tg.util import Bunch
from tg.configuration.sqla.balanced_session import force_request_engine
from tg.flash import flash
from tg.caching import beaker_cache, cached_property, _cached_call
from tg.predicates import NotAuthorizedError
from tg._compat import default_im_func, unicode_text
from webob.acceptparse import Accept
from .validation import _ValidationIntent
from tg.configuration import milestones
import tg

import logging

log = logging.getLogger(__name__)


def _decorated_controller_caller(tg_config, controller, remainder, params):
    try:
        application_controller_caller = tg_config['controller_caller']
    except KeyError:
        application_controller_caller = call_controller

    return application_controller_caller(tg_config, controller, remainder, params)


class Decoration(object):
    """ Simple class to support 'simple registration' type decorators
    """
    def __init__(self, controller):
        self.controller = controller
        self.controller_caller = _decorated_controller_caller
        self._expositions = []
        self.engines = {}
        self.engines_keys = []
        self.default_engine = None
        self.custom_engines = {}
        self.render_custom_format = None
        self.validations = []
        self.inherit = False
        self.requirements = []
        self.hooks = dict(before_validate=[],
                          before_call=[],
                          before_render=[],
                          after_render=[])

    def __repr__(self): # pragma: no cover
        return '<Decoration %s for %r>' % (id(self), self.controller)

    @classmethod
    def get_decoration(cls, func):
        try:
            dec = func.decoration
        except:
            dec = func.decoration = cls(func)
        return dec

    def _register_exposition(self, exposition, inherit=False, before=False):
        """Register an exposition for later application"""

        # We need to store a reference to the exposition
        # so that we can merge them when inheritance is performed
        if before:
            self._expositions.insert(0, exposition)
        else:
            self._expositions.append(exposition)

        if inherit:
            # if at least one exposition is in inherit mode
            # all of them must inherit
            self.inherit = True

        milestones.renderers_ready.register(self._resolve_expositions)

    def _resolve_expositions(self):
        """Applies all the registered expositions"""
        while True:
            try:
                exposition = self._expositions.pop(0)
                exposition._apply()
            except IndexError:
                break

    @property
    def requirement(self):  # pragma: no cover
        warnings.warn("Decoration.requirement is deprecated, "
                      "please use 'requirements' instead", DeprecationWarning)
        try:
            return self.requirements[0]
        except IndexError:
            return None

    @property
    def exposed(self):
        return bool(self.engines) or bool(self.custom_engines)

    @property
    def validation(self):
        warnings.warn("Decoration.validation is deprecated, "
                      "please use 'validations' instead", DeprecationWarning)
        try:
            return self.validations[0]
        except IndexError:
            return None

    def merge(self, deco):
        # This merges already registered template engines
        self.engines = dict(tuple(deco.engines.items()) + tuple(self.engines.items()))
        self.engines_keys = sorted(self.engines, reverse=True)
        self.custom_engines = dict(tuple(deco.custom_engines.items()) + tuple(self.custom_engines.items()))

        # This merges yet to register template engines
        for exposition in reversed(deco._expositions):
            self._register_exposition(exposition._clone(self.controller), before=True)

        # inherit all the parent hooks
        # parent hooks before current hooks so that they get called before
        for hook_name, hooks in deco.hooks.items():
            self.hooks[hook_name] = hooks + self.hooks[hook_name]

        # Inherit al validators registered on parent.
        self.validations = deco.validations + self.validations

    def run_hooks(self, tgl, hook, *l, **kw):
        warnings.warn("Decoration.run_hooks is deprecated, "
                      "please use tg.hooks.notify instead", DeprecationWarning)
        tg.hooks.notify(hook, args=l, kwargs=kw,
                        controller=self.controller, context_config=tgl.config)

    def register_hook(self, hook_name, func): #pragma: no cover
        warnings.warn("Decoration.register_hook is deprecated, "
                      "please use tg.hooks.register instead", DeprecationWarning)
        tg.hooks.register(hook_name, func, controller=self.controller)

    def register_template_engine(self,
            content_type, engine, template, exclude_names, render_params):
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

        render_params registers extra parameters which will be sent
        to the rendering method.  This allows you to influence things
        like the rendering method or the injected doctype.

        """
        default_renderer = config.get('default_renderer')
        available_renderers = config.get('renderers', [])

        if engine and not available_renderers:
            log.warn('Renderers not registered yet while exposing template %s for engine %s, '
                     'skipping engine availability check', template, engine)

        if engine and available_renderers and engine not in available_renderers:
            log.debug('Registering template %s for engine %s not available. Skipping it', template, engine)
            return

        content_type = content_type or '*/*'

        try:
            current_content_type_engine = self.engines[content_type][0]
        except (KeyError, IndexError):
            current_content_type_engine = None

        if current_content_type_engine is not None and engine != default_renderer:
            # Avoid overwriting the default renderer when there is already a template registered
            return

        self.engines[content_type] = (engine, template, exclude_names, render_params or {})

        # Avoid engine lookup if we have only one engine registered
        if len(self.engines) == 1:
            self.default_engine = content_type
        else:
            self.default_engine = None

        # This is a hack to make text/html prominent in respect to other common choices
        # when they have the same weight for webob.acceptparse.Accept.best_match().
        # It uses the fact that the most common content types are all alphabetically
        # precedent to text/html, and so sorting engine keys alphabetically reversed
        # should make text/html the first choice when no other better choices are available.
        self.engines_keys = sorted(self.engines, reverse=True)

    def register_custom_template_engine(self, custom_format,
            content_type, engine, template, exclude_names, render_params):
        """Registers a custom engine on the controller.

        Multiple engines can be registered, but only one engine per
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

        render_params registers extra parameters which will be sent
        to the rendering method.  This allows you to influence things
        like the rendering method or the injected doctype.

        """

        self.custom_engines[custom_format or '"*/*"'] = (
            content_type, engine, template, exclude_names, render_params or {})

    def lookup_template_engine(self, tgl):
        """Return the template engine data.

        Provides a convenience method to get the proper engine,
        content_type, template, and exclude_names for a particular
        tg_format (which is pulled off of the request headers).

        """
        request = tgl.request
        response = tgl.response

        try:
            render_custom_format = request._render_custom_format[self.controller]
        except:
            render_custom_format = self.render_custom_format

        if render_custom_format:
            (content_type, engine, template, exclude_names, render_params
                ) = self.custom_engines[render_custom_format]
        else:
            if self.default_engine:
                content_type = self.default_engine
            elif self.engines:
                if request._response_type and request._response_type in self.engines:
                    accept_types = request._response_type
                else:
                    accept_types = request.headers.get('accept', '*/*')
                content_type = Accept(accept_types).best_match(self.engines_keys, self.engines_keys[0])
            else:
                content_type = 'text/html'

            # check for overridden content type from the controller call
            try:
                controller_content_type = response.headers['Content-Type']
                # make sure we handle content_types like 'text/html; charset=utf-8'
                content_type = controller_content_type.split(';')[0]
            except KeyError:
                pass

            # check for overridden templates
            try:
                cnt_override_mapping = request._override_mapping[self.controller]
                engine, template, exclude_names, render_params = cnt_override_mapping[content_type.split(";")[0]]
            except (AttributeError, KeyError):
                (engine, template, exclude_names, render_params
                    ) = self.engines.get(content_type, (None,) * 4)

        if 'charset' not in content_type and (content_type.startswith('text')
                or  content_type in ('application/xhtml+xml',
                        'application/xml', 'application/json')):
            content_type += '; charset=utf-8'

        return content_type, engine, template, exclude_names, render_params

    def _register_hook(self, hook_name, func):
        """Registers the specified function as a hook.

        This is internal API which is used by tg.hooks, instead of
        calling this tg.hooks.register should be used.

        We now have four core hooks that can be applied by adding
        decorators: before_validate, before_call, before_render, and
        after_render. register_hook attaches the function to the hook
        which get's called at the appropriate time in the request life
        cycle.)
        """
        self.hooks.setdefault(hook_name, []).append(func)

    def _register_requirement(self, requirement):
        self._register_hook('before_call', requirement._check_authorization)
        self.requirements.append(requirement)

    def _register_controller_wrapper(self, wrapper):
        try:
            self.controller_caller = wrapper(self.controller_caller)
        except TypeError:
            self.controller_caller = _DeprecatedControllerWrapper(wrapper, tg.config,
                                                                  self.controller_caller)

    def _register_validation(self, validation):
        self.validations.insert(0, validation)


class _hook_decorator(object):
    """Superclass for all the specific TG2 hook validators.

    Its `hook_name` must be overridden by a specific hook.

    """

    hook_name = None

    def __init__(self, hook_func):
        if hasattr(hook_func, '__name__'):
            self.__name__ = hook_func.__name__
        if hasattr(hook_func, '__doc__'):
            self.__doc__ = hook_func.__doc__
        self.hook_func = hook_func

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco._register_hook(self.hook_name, self.hook_func)
        return func


class before_validate(_hook_decorator):
    """A list of callables to be run before validation is performed."""

    hook_name = 'before_validate'


class before_call(_hook_decorator):
    """A list of callables to be run before the controller method is called."""

    hook_name = 'before_call'


class before_render(_hook_decorator):
    """A list of callables to be run before the template is rendered."""

    hook_name = 'before_render'


class after_render(_hook_decorator):
    """A list of callables to be run after the template is rendered.

    Will be run before it is returned returned up the WSGI stack.

    """

    hook_name = 'after_render'


class expose(object):
    """Register attributes on the decorated function.

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
      custom_format
        Registers as a custom format which can later be activated calling
        use_custom_format
      render_params
        Assign parameters that shall be passed to the rendering method.
      inherit
        Inherit all the decorations from the same method in the parent
        class. This will let the exposed method expose the same template
        as the overridden method template and keep the same hooks and
        validation that the parent method had.

    The expose decorator registers a number of attributes on the
    decorated function, but does not actually wrap the function the way
    TurboGears 1.0 style expose decorators did.

    This means that we don't have to play any kind of special tricks to
    maintain the signature of the exposed function.

    The exclude_names parameter is new, and it takes a list of keys that
    ought to be scrubbed from the dictionary before passing it on to the
    rendering engine.  This is particularly useful for JSON.

    The render_parameters is also new.  It takes a dictionary of arguments
    that ought to be sent to the rendering engine, like this::

        render_params={'method': 'xml', 'doctype': None}

    Expose decorator can be stacked like this::

        @expose('json', exclude_names='d')
        @expose('kid:blogtutorial.templates.test_form',
                content_type='text/html')
        @expose('kid:blogtutorial.templates.test_form_xml',
                content_type='text/xml', custom_format='special_xml')
        def my_exposed_method(self):
            return dict(a=1, b=2, d="username")

    The expose('json') syntax is a special case.  json is a
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

    The last expose decorator example uses the custom_format parameter
    which takes an arbitrary value (in this case 'special_xml').
    You can then use the`use_custom_format` function within the method
    to decide which of the 'custom_format' registered expose decorators
    to use to render the template.

    """

    def __init__(self, template='', content_type=None, exclude_names=None,
                 custom_format=None, render_params=None, inherit=False):

        self.engine = None
        self.template = template
        self.content_type = content_type
        self.exclude_names = exclude_names
        self.custom_format = custom_format
        self.render_params = render_params

        self.inherit = inherit
        self._func = None

    def __call__(self, func):
        self._func = func
        deco = Decoration.get_decoration(func)
        deco._register_exposition(self, self.inherit)
        return func

    def _resolve_options(self):
        """This resolves exposition options that depend on
        configuration steps that might not have already happened.
        It's automatically called by _apply when required

        """
        if self.engine is not None:
            return

        exclude_names = self.exclude_names
        template = self.template
        content_type = self.content_type

        if exclude_names is None:
            exclude_names = []

        if template in config.get('renderers', []):
            engine, template = template, ''
        elif ':' in template:
            engine, template = template.split(':', 1)
        elif template:
            # Use the default templating engine from the config
            engine = config.get('default_renderer')
        else:
            engine, template = None, None

        if content_type is None:
            all_engines_options = config.get('rendering_engines_options', {})
            engine_options = all_engines_options.get(engine, {})
            content_type = engine_options.get('content_type', 'text/html')

        engines_without_vars = config.get('rendering_engines_without_vars', [])
        if engine in engines_without_vars and 'tmpl_context' not in exclude_names:
            exclude_names.append('tmpl_context')

        self.engine = engine
        self.template = template
        self.content_type = content_type
        self.exclude_names = exclude_names

    def _clone(self, func):
        clone = copy.copy(self)
        clone._func = func
        return clone

    def _apply(self):
        """Applies an exposition for real"""
        if self._func is None:
            log.error('Applying an exposition with no decorated function!')
            return

        self._resolve_options()

        deco = Decoration.get_decoration(self._func)
        if deco.inherit and not self.template and not self.engine:
            # If we are just inheriting without adding additional
            # engines or templates we can just skip this part.
            return

        if self.custom_format:
            deco.register_custom_template_engine(
                self.custom_format, self.content_type, self.engine,
                self.template, self.exclude_names, self.render_params)
        else:
            deco.register_template_engine(
                self.content_type, self.engine,
                self.template, self.exclude_names, self.render_params)


def use_custom_format(controller, custom_format):
    """Use use_custom_format in a controller in order to change
    the active @expose decorator when available."""
    deco = Decoration.get_decoration(controller)

    # Check the custom_format passed is available for use
    if custom_format not in deco.custom_engines:
        raise ValueError("'%s' is not a valid custom_format" % custom_format)

    try:
        render_custom_format = request._render_custom_format
    except AttributeError:
        render_custom_format = request._render_custom_format = {}
    render_custom_format[default_im_func(controller)] = custom_format


def override_template(view, template):
    """Override the template to be used.

    Use override_template in a controller method in order to change the template
    that will be used to render the response dictionary dynamically.

    The ``view`` argument is the actual controller method for which you
    want to replace the template.

    The ``template`` string passed in requires that
    you include the template engine name, even if you're using the default.

    So you have to pass in a template id string like::

       "genshi:myproject.templates.index2"

    future versions may make the `genshi:` optional if you want to use
    the default engine.

    """
    try:
        engines = view.decoration.engines
    except:
        return

    for content_type, content_engine in engines.items():
        tmpl = template.split(':', 1)
        tmpl.extend(content_engine[2:])
        try:
            override_mapping = request._override_mapping
        except AttributeError:
            override_mapping = request._override_mapping = {}
        override_mapping.setdefault(default_im_func(view), {}).update({content_type: tmpl})


class validate(_ValidationIntent):
    """Registers which validators ought to be applied.

    If you want to validate the contents of your form,
    you can use the ``@validate()`` decorator to register
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
        super(validate, self).__init__(validators or form, error_handler)

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco._register_validation(self)
        return func


class decode_params(object):
    """Decorator that enables parsing parameters from request body.

    By default the arguments are parsed in **JSON** format (which is
    currently the only supported format).

    """
    def __init__(self, format='json'):
        if format not in ('json', ):
            raise ValueError('Currently only JSON format is supported')

        self._format = format

    def run_hook(self, remainder, params):
        if self._format == 'json' and request.content_type == 'application/json':
            params.update(request.json_body)

    def __call__(self, func):
        decoration = Decoration.get_decoration(func)
        decoration._register_hook('before_validate', self.run_hook)
        return func


class paginate(object):
    """Paginate a given collection.

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

      ${tmpl_context.paginators.<name>.pager()}

    It is possible to have several :func:`paginate`-decorators for
    one controller action to paginate several collections independently
    from each other. If this is desired, don't forget to set the :attr:`use_prefix`-parameter
    to :const:`True`.

    :Parameters:
      name
        the collection to be paginated.
      items_per_page
        the number of items to be rendered. Defaults to 10
      max_items_per_page
        the maximum number of items allowed to be set via parameter.
        Defaults to 0 (does not allow to change that value).
      use_prefix
        if True, the parameters the paginate
        decorator renders and reacts to are prefixed with
        "<name>_". This allows for multi-pagination.

    """

    def __init__(self, name, use_prefix=False,
        items_per_page=10, max_items_per_page=0):
        self.name = name
        prefix = use_prefix and name + '_' or ''
        self.page_param = prefix + 'page'
        self.items_per_page_param = prefix + 'items_per_page'
        self.items_per_page = items_per_page
        self.max_items_per_page = max_items_per_page

    def __call__(self, func):
        decoration = Decoration.get_decoration(func)
        decoration._register_hook('before_validate', self.before_validate)
        decoration._register_hook('before_render', self.before_render)
        return func

    def before_validate(self, remainder, params):
        page_param = params.pop(self.page_param, None)
        if page_param:
            try:
                page = int(page_param)
                if page < 1:
                    raise ValueError
            except ValueError:
                page = 1
        else:
            page = 1

        try:
            paginators_data = request.paginators
        except:
            paginators_data = request.paginators = {'_tg_paginators_params':{}}

        paginators_data['_tg_paginators_params'][self.page_param] = page_param
        paginators_data[self.name] = paginator = Bunch()

        paginator.paginate_page = page or 1
        items_per_page = params.pop(self.items_per_page_param, None)
        if items_per_page:
            try:
                items_per_page = min(
                    int(items_per_page), self.max_items_per_page)
                if items_per_page < 1:
                    raise ValueError
            except ValueError:
                items_per_page = self.items_per_page
        else:
            items_per_page = self.items_per_page
        paginator.paginate_items_per_page = items_per_page
        paginator.paginate_params = params.copy()
        paginator.paginate_params.update(paginators_data['_tg_paginators_params'])
        if items_per_page != self.items_per_page:
            paginator.paginate_params[self.items_per_page_param] = items_per_page

    def before_render(self, remainder, params, output):
        if not isinstance(output, dict) or not self.name in output:
            return

        paginator = request.paginators[self.name]
        collection = output[self.name]
        page = Page(collection, paginator.paginate_page, paginator.paginate_items_per_page)
        page.kwargs = paginator.paginate_params
        if self.page_param != 'name':
            page.pager = partial(page.pager, page_param=self.page_param)
        if not getattr(tmpl_context, 'paginators', None):
            tmpl_context.paginators = Bunch()
        tmpl_context.paginators[self.name] = output[self.name] = page

@before_validate
def https(remainder, params):
    """Ensure that the decorated method is always called with https."""
    if request.scheme.lower() == 'https': return
    if request.method.upper() == 'GET':
        redirect('https' + request.url[len(request.scheme):])
    raise HTTPMethodNotAllowed(headers=dict(Allow='GET'))


_variabledecode = None
@before_validate
def variable_decode(remainder, params):
    """Best-effort formencode.variabledecode on the params before validation.

    If any exceptions are raised due to invalid parameter names, they are
    silently ignored, hopefully to be caught by the actual validator.
    Note that this decorator will *add* parameters to the method, not remove.
    So for instance a method will move from {'foo-1':'1', 'foo-2':'2'}
    to {'foo-1':'1', 'foo-2':'2', 'foo':['1', '2']}.

    """
    global _variabledecode
    if _variabledecode is None:
        from formencode import variabledecode as _variabledecode

    try:
        new_params = _variabledecode.variable_decode(params)
        params.update(new_params)
    except:
        pass


@before_validate
def without_trailing_slash(remainder, params):
    """This decorator allows you to ensure that the URL does not end in "/".

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
    req = request._current_obj()
    if req.method == 'GET' and req.path.endswith('/') and not(req._response_type) and len(req.params)==0:
        redirect(request.url[:-1], redirect_with=HTTPMovedPermanently)


@before_validate
def with_trailing_slash(remainder, params):
    """This decorator allows you to ensure that the URL ends in "/".

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
    req = request._current_obj()
    if (req.method == 'GET' and not(req.path.endswith('/')) and not(req._response_type) and len(req.params)==0):
        redirect(request.url+'/', redirect_with=HTTPMovedPermanently)


class require(object):
    """
    Decorator that checks if the specified predicate it met, if it isn't
    it calls the denial_handler to prevent access to the decorated method.

    The default authorization denial handler of this protector will flash
    the message of the unmet predicate with ``warning`` or ``error`` as the
    flash status if the HTTP status code is 401 or 403, respectively.

    :param predicate: An object with a check_authorization(environ) method which
        must raise a tg.predicates.NotAuthorizedError if not met.
    :param denial_handler: The callable to be run if authorization is
        denied (overrides :attr:`default_denial_handler` if defined).
    :param smart_denial: A list of response types for which to trigger
        the smart denial, which will act as an API providing a pass-through
        :func:`tg.controllers.util.abort`.
        If ``True``, ``('application/json', 'text/xml')`` will be used.

    If called, ``denial_handler`` will be passed a positional argument
    which represents a message on why authorization was denied.

    Use ``allow_only`` property of ``TGController`` for controller-wide authorization.

    """
    def __init__(self, predicate, denial_handler=None, smart_denial=False):
        self.predicate = predicate
        self.denial_handler = denial_handler or self.default_denial_handler

        if smart_denial is True:
            smart_denial = ('application/json', 'text/xml')
        self.smart_denial = smart_denial

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco._register_requirement(self)
        return func

    def _check_authorization(self, *args, **kwargs):
        req = request._current_obj()

        try:
            self.predicate.check_authorization(req.environ)
        except NotAuthorizedError as e:
            reason = unicode_text(e)
            if req.environ.get('repoze.who.identity'):
                # The user is authenticated.
                code = 403
            else:
                # The user is not authenticated.
                code = 401
            response.status = code
            return self.denial_handler(reason)

    def default_denial_handler(self, reason):
        """Authorization denial handler for protectors."""
        passthrough_abort = False

        if self.smart_denial:
            response_type = response.content_type or request.response_type
            if response_type in self.smart_denial:
                # It's an API response, use a pass-through abort
                passthrough_abort = True
                if response_type == 'application/json':
                    passthrough_abort = 'json'

        if passthrough_abort is False:
            # Plain HTML page
            status = 'warning' if response.status_int == 401 else 'error'
            flash(reason, status=status)

        abort(response.status_int, reason, passthrough=passthrough_abort)


class with_engine(object):
    """
    Decorator to force usage of a specific database engine
    in TurboGears SQLAlchemy BalancedSession.

    :param engine_name: 'master' or the name of one of the slaves, if is ``None``
             it will not force any specific engine.
    :param master_params: A dictionary or GET parameters that when present will force
             usage of the master node. The keys of the dictionary will be the
             name of the parameters to look for, while the values must be whenever
             to pop the paramter from the parameters passed to the controller (True/False).
             If `master_params` is a list then it is converted to a dictionary where
             the keys are the entries of the list and the value is always True.
    """

    def __init__(self, engine_name=None, master_params={}):
        self.engine_name = engine_name

        if not hasattr(master_params, 'keys'):
            self.master_params = dict((p, True) for p in master_params)
        else:
            self.master_params = master_params

    def before_validate(self, remainder, params):
        force_request_engine(self.engine_name)
        for p, pop in self.master_params.items():
            if p in params:
                if pop:
                    v = params.pop(p, None)
                else:
                    v = params.get(p)

                if v:
                    force_request_engine('master')
                    break

    def __call__(self, func):
        decoration = Decoration.get_decoration(func)
        decoration._register_hook('before_validate', self.before_validate)
        return func


class cached(object):
    """
    Decorator to cache the controller, if you also want to cache
    template remember to return ``tg_cache`` option from the controller.

    The following parameters are accepted:

    ``key`` - Specifies the controller parameters used to generate the cache key.
        NoDefault - Uses function name and all request parameters as the key (default)

        None - No variable key, uses only function name as key

        string - Use function name and only "key" parameter

        list - Use function name and all parameters listed
    ``expire``
        Time in seconds before cache expires, or the string "never".
        Defaults to "never"
    ``type``
        Type of cache to use: dbm, memory, file, memcached, or None for
        Beaker's default
    ``cache_headers``
        A tuple of header names indicating response headers that
        will also be cached.
    ``invalidate_on_startup``
        If True, the cache will be invalidated each time the application
        starts or is restarted.
    ``cache_response``
        Determines whether the response at the time the cache is used
        should be cached or not, defaults to True.

        .. note::
            When cache_response is set to False, the cache_headers
            argument is ignored as none of the response is cached.
    """
    def __init__(self, key=NoDefault, expire="never", type=None,
                 query_args=None,  # Backward compatibility, actually ignored
                 cache_headers=('content-type', 'content-length'),
                 invalidate_on_startup=False, cache_response=True,
                 **b_kwargs):
        self.key = key
        self.expire = expire
        self.type = type
        self.cache_headers = cache_headers
        self.invalidate_on_startup = invalidate_on_startup
        self.cache_response = cache_response
        self.beaker_options = b_kwargs

    def __call__(self, func):
        decoration = Decoration.get_decoration(func)

        def controller_wrapper(__, next_caller):
            if self.invalidate_on_startup:
                starttime = time.time()
            else:
                starttime = None

            def cached_call_controller(controller, remainder, params):
                if self.key:
                    key_dict = request.args_params
                    if self.key != NoDefault:
                        if isinstance(self.key, (list, tuple)):
                            key_dict = dict((k, key_dict[k]) for k in key_dict)
                        else:
                            key_dict = {self.key: key_dict[self.key]}
                else:
                    key_dict = {}

                return _cached_call(next_caller, (controller, remainder, params), {},
                                    key_func=func, key_dict=key_dict,
                                    expire=self.expire, type=self.type,
                                    starttime=starttime, cache_headers=self.cache_headers,
                                    cache_response=self.cache_response,
                                    cache_extra_args=self.beaker_options)

            return cached_call_controller

        decoration._register_controller_wrapper(controller_wrapper)
        return func
