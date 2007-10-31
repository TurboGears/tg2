"""Classes and methods for TurboGears decorators"""
import formencode
from paste.util.mimeparse import best_match
import pylons

def _schema(d=None, **kw):
    dd = {}
    if d:
        dd.update(d)
    dd.update(**kw)
    return formencode.Schema.__metaclass__('schema', (formencode.Schema,), dd)

class TGDecoration(object):

    def __init__(self):
        self.engines = {}
        self.validator = None
        self.error_handler = None
        self.hooks = dict(
            before_validate=[],
            before_call=[],
            before_render=[],
            after_render=[])


    @classmethod
    def get_decoration(klass, func):
        if not hasattr(func, 'tg_info'):
            func.tg_info=klass()
        return func.tg_info

    @property
    def exposed(self):
        if self.engines: return True
        else: return False

    def run_hooks(self, hook, *l, **kw):
        for func in self.hooks[hook]:
            func(*l, **kw)

    def register_template_engine(self, content_type, engine, template, exclude_names):
        '''Regesters an engine on the controller.
        
        Multiple engines can be regestered, but only one engine per content_type.   
        If no content type is specified the engine is regestered at */* which is the 
        default, and will be used whenever no content type is specified.  
        
        exclude_names keeps track of a list of keys which will be removed from the 
        controller's dictionary before it is loaded into the template.  This allows you to 
        exclude some information from JSONification, and other 'automatic' engines which 
        don't require a template.
        '''
        #TODO: Are there some other things like lookup paths which need to be setup here?
        if content_type is None:
            content_type = '*/*'
        self.engines[content_type] = engine, template, exclude_names

    def lookup_template_engine(self, request):
        '''Provides a convenience method to get the proper engine, content_type, template, 
        and exclude_names for a particular tg_format (which is pulled off of the request
        headers)."
        '''
        tg_format = request.headers.get('tg_format')
        if tg_format:
            assert '/' in tg_format, 'Invalid tg_format: must be a MIME type'
            accept_types = tg_format
        else: accept_types = request.headers.get('accept', '*/*')
        content_type = best_match(self.engines.keys(), accept_types)
        engine, template, exclude_names = self.engines[content_type]
        return content_type, engine, template, exclude_names

    def register_hook(self, hook_name, func):
        '''We now have four core hooks that can be applied by adding decorators: 
        before_validate, before_call, before_render, and after_render.   regester_hook attaches the
        function to the hook which get's called at the apropriate time in the request life cycle.)
        '''
        self.hooks[hook_name].append(func)

class _hook_decorator(object):
    hook_name=None # must be overridden

    def __init__(self, hook_func):
        self.hook_func = hook_func

    def __call__(self, func):
        deco = TGDecoration.get_decoration(func)
        deco.register_hook(self.hook_name, self.hook_func)
        return func

class before_validate(_hook_decorator):
    hook_name = 'before_validate'
    
class before_call(_hook_decorator):
    hook_name = 'before_call'
    
class before_render(_hook_decorator):
    hook_name = 'before_render'
    
class after_render(_hook_decorator):
    hook_name = 'after_render'

class expose(object):
    """
    regesters attributes on the decorated function
    
    :Parameters:
      template
        Assign a template, you could use the syntax 'genshi:template' to 
        use different templates. 
        The default template engine is genshi.
      content_type
        Assign content type.
        The default content type is 'text/html'.
      exclude_names
        Assign exclude names
        
    The expose decorator regesters a number of attributes on the decorated function, but 
    does not actually wrap the function the way TurboGears 1.0 style expose decorators did. 
    
    This means that we don't have to play any kind of special tricks to maintain the signature 
    of the exposed function.
    
    The exclude_names parameter is new, and it takes a list of keys that ought to be scrubbed
    from the dictinary before passing it on to the rendering engine.   This is particularly 
    usefull for JSON. 
    
    Expose decorator can be stacked like this::
    
        @expose('json', exclude_names='d')
        @expose('kid:blogtutorial.templates.test_form', content_type='text/html')
        def my_exposed_method(self):
            return dict(a=1, b=2, d="username")
    
    the expose('json') syntax is a special case.  json is a buffet rendering engine, but unlike others
    it does not require a template, and expose assumes that it matches content_type='application/json'
    
    Otherwise expose assumes that the template is for html.   All other content_types must 
    be explicitly matched to a template and engine.
    
    """
    def __init__(self, template='', content_type=None, exclude_names=None):
        if exclude_names is None:
            exclude_names = []    
        if template == 'json':
            engine, template = 'json', ''
        elif ':' in template:
            engine, template = template.split(':', 1)
        elif template:
            #TODO: lookup the default template engine from the config.
            engine, template = 'genshi', template
        else:
            engine, template = None, None
        if content_type is None:
            if engine == 'json': content_type = 'application/json'
            else: content_type = 'text/html'
        if engine == 'json' and 'context' not in exclude_names:
            exclude_names.append('context')
        self.engine = engine
        self.template = template
        self.content_type = content_type
        self.exclude_names = exclude_names

    def __call__(self, func):
        deco = TGDecoration.get_decoration(func)
        deco.register_template_engine(
            self.content_type, self.engine, self.template, self.exclude_names)
        return func

#TODO: Consider depricating this in favor of pylons validate decorator
class validate(object):
    """Validate regesters validator on the decorated function.
    
    :Parameters:
      validator
        Valdators
      error_handler
        Assign error handler
    """
    def __init__(self, validator=None, error_handler=None, **kw):
        if not hasattr(validator, 'to_python') and hasattr(validator, 'validator'):
            validator = validator.validator
        elif kw:
            assert validator is None, \
                   'validator must not be specified with additional keyword arguments'
            validator = kw
        if not isinstance(validator, formencode.Schema):
            validator = _schema(validator)
        self.validator = validator
        self.error_handler = error_handler

    def __call__(self, func):
        deco = TGDecoration.get_decoration(func)
        deco.validator = self.validator
        deco.error_handler = self.error_handler
        return func
