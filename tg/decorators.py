"""Decorators use by the TurboGears controllers

These decorators are not traditonal wrappers.  They  are much simplified from the
turbogears 1 decorators, because all they do is regester attributes on
the functions they wrap, and then the DecoratedController provides the hooks
needed to support these decorators."""

import formencode
from paste.util.mimeparse import best_match
from decorator import decorator

from webob.multidict import MultiDict
from webhelpers.paginate import Page
from tg.configuration import Bunch
# this can't be tg, as we are circular importing then!
from pylons import config, request
from pylons import tmpl_context as c
from util import partial

class Decoration(object):
    """ Simple class to support 'simple registration' type decorators
    """
    def __init__(self):
        self.engines = {}
        self.validation = None
        self.error_handler = None
        self.hooks = dict(before_validate=[],
                          before_call=[],
                          before_render=[],
                          after_render=[])

    def get_decoration(cls, func):
        if not hasattr(func, 'decoration'):
            func.decoration = cls()
        return func.decoration
    get_decoration = classmethod(get_decoration)

    def exposed(self):
        return bool(self.engines)
    expose = property(exposed)

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

    def lookup_template_engine(self, request):
        """Return the template engine data.

        Provides a convenience method to get the proper engine,
        content_type, template, and exclude_names for a particular
        tg_format (which is pulled off of the request headers)."
        """
        tg_format = request.headers.get('tg_format')
        if tg_format:
            assert '/' in tg_format, 'Invalid tg_format: must be a MIME type'
            accept_types = tg_format
        else:
            accept_types = request.headers.get('accept', '*/*')
        content_type = best_match(self.engines.keys(), accept_types)
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
        def my_exposed_method(self):
            return dict(a=1, b=2, d="username")

    The expose('json') syntax is a special case.  json is a buffet
    rendering engine, but unlike others it does not require a template,
    and expose assumes that it matches content_type='application/json'

    Otherwise expose assumes that the template is for html.  All other
    content_types must be explicitly matched to a template and engine.
    """

    def __init__(self, template='', content_type=None, exclude_names=None):
        if exclude_names is None:
            exclude_names = []
        if template == 'json':
            engine, template = 'json', ''
        elif ':' in template:
            engine, template = template.split(':', 1)
        elif template:
            # Use the default templating engine from the config
            from pylons import config
            engine = config['buffet.template_engines'][0]['engine']
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

    def __call__(self, func):
        deco = Decoration.get_decoration(func)
        deco.register_template_engine(
            self.content_type, self.engine, self.template, self.exclude_names)
        return func

def override_template(controller, template):
    """Use overide_template in a controller in order to change the
    template that will be used to render the response dictionary
    dynamically."""
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
    engines['text/html'] = template


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


def paginate(name, items_per_page=10, use_prefix=False):
    """
    Paginate a given collection.

    This decorator is mainly exposing the functionality
    of webhelpers.paginate.

    To render the actual pager, use

      ${c.paginators.<name>.pager()}

    where c is the tmpl_context.


    :Parameters:
      name
        the collection to be paginated.
      items_per_page
        the number of items to be rendered. Defaults to 10
      use_prefix
        if True, the parameters the paginate
        decorator renders and reacts to are prefixed with
        "name_". This allows for multi-pagination.

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
            real_items_per_page = int(kwargs.pop(own_parameters['items_per_page'], items_per_page))
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
                page.pager = partial(page.pager, page_param=own_parameters["page"])
                res[name] = page
                # this is a bit strange - it appears
                # as if c returns an empty
                # string for everything it dosen't know.
                # I didn't find that documented, so I
                # just put this in here and hope it works.
                if type(c.paginators) == str:
                    c.paginators = Bunch()
                c.paginators[name] = page
            return res
        return _w
    return _d

@decorator
def postpone_commits(func, *args, **kwargs):
    #TODO: Test and document this.
    s = config.get('DBSession', None)
    assert hasattr(s, 'commit')
    old_commit = s.commit
    s.commit = s.flush
    retval = func(*args, **kwargs)
    s.commit = old_commit
    return retval
    

