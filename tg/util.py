"""Utilities"""
from pkg_resources import resource_filename
import warnings
from tg.request_local import request


class DottedFileLocatorError(Exception):pass

def get_partial_dict(prefix, dictionary):
    """Given a dictionary and a prefix, return a Bunch, with just items
    that start with prefix

    The returned dictionary will have 'prefix.' stripped so:

    get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3})

    would return:

    {'xyz':1,'zyx':2}
    """

    match = prefix + "."
    n = len(match)

    new_dict = Bunch([(key[n:], dictionary[key])
                       for key in dictionary.keys()
                       if key.startswith(match)])
    if new_dict:
        return new_dict
    else:
        raise AttributeError

class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __getitem__(self, key):
        return  dict.__getitem__(self, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return get_partial_dict(name, self)

    __setattr__ = dict.__setitem__

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


def partial(*args, **create_time_kwds):
    func = args[0]
    create_time_args = args[1:]
    def curried_function(*call_time_args, **call_time_kwds):
        args = create_time_args + call_time_args
        kwds = create_time_kwds.copy()
        kwds.update(call_time_kwds)
        return func(*args, **kwds)
    return curried_function

class DottedFileNameFinder(object):
    """this class implements a cache system above the
    get_dotted_filename function and is designed to be stuffed
    inside the app_globals.

    It exposes a method named get_dotted_filename with the exact
    same signature as the function of the same name in this module.

    The reason is that is uses this function itself and just adds
    caching mechanism on top.
    """
    def __init__(self):
        self.__cache = dict()

    def get_dotted_filename(self, template_name, template_extension='.html'):
        """this helper function is designed to search a template or any other
        file by python module name.

        Given a string containing the file/template name passed to the @expose
        decorator we will return a resource useable as a filename even
        if the file is in fact inside a zipped egg.

        The actual implementation is a revamp of the Genshi buffet support
        plugin, but could be used with any kind a file inside a python package.

        @param template_name: the string representation of the template name
        as it has been given by the user on his @expose decorator.
        Basically this will be a string in the form of:
        "genshi:myapp.templates.somename"
        @type template_name: string

        @param template_extension: the extension we excpect the template to have,
        this MUST be the full extension as returned by the os.path.splitext
        function. This means it should contain the dot. ie: '.html'

        This argument is optional and the default value if nothing is provided will
        be '.html'
        @type template_extension: string
        """
        try:
            return self.__cache[template_name]
        except KeyError:
            # the template name was not found in our cache
            divider = template_name.rfind('.')
            if divider >= 0:
                package = template_name[:divider]
                basename = template_name[divider + 1:] + template_extension
                try:
                    result = resource_filename(package, basename)
                except ImportError as e:
                    raise DottedFileLocatorError(str(e) +". Perhaps you have forgotten an __init__.py in that folder.")
            else:
                result = template_name

            self.__cache[template_name] = result

            return result

def wrap(wrapper, wrapped):
    """Update a wrapper function to look like the wrapped function"""
    for attr in ('__module__', '__name__', '__doc__'):
        setattr(wrapper, attr, getattr(wrapped, attr))
    for attr in     ('__dict__',):
        getattr(wrapper, attr).update(getattr(wrapped, attr, {}))
    # Return the wrapper so this can be used as a decorator via partial()
    return wrapper


def no_warn(f, *args, **kwargs):
    def _f(*args, **kwargs):
        warnings.simplefilter("ignore")
        f(*args, **kwargs)
        warnings.resetwarnings()
    return wrap(_f, f)

class LazyString(object):
    """Has a number of lazily evaluated functions replicating a
    string. Just override the eval() method to produce the actual value.
    """
    def __init__(self, func, *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def eval(self):
        return self.func(*self.args, **self.kwargs)

    def __unicode__(self):
        return unicode(self.eval())

    def __str__(self):
        return str(self.eval())

    def __mod__(self, other):
        return self.eval() % other

    def format(self, other):
        return self.eval().format(other)

def lazify(func):
    """Decorator to return a lazy-evaluated version of the original"""
    def newfunc(*args, **kwargs):
        return LazyString(func, *args, **kwargs)
    newfunc.__name__ = 'lazy_%s' % func.__name__
    newfunc.__doc__ = 'Lazy-evaluated version of the %s function\n\n%s' % \
        (func.__name__, func.__doc__)
    return newfunc

def call_controller(controller, remainder, params):
    return controller(*remainder, **params)


class ContextObj(object):
    def __repr__(self):
        attrs = sorted((name, value)
                       for name, value in self.__dict__.items()
                       if not name.startswith('_'))
        parts = []
        for name, value in attrs:
            value_repr = repr(value)
            if len(value_repr) > 70:
                value_repr = value_repr[:60] + '...' + value_repr[-5:]
            parts.append(' %s=%s' % (name, value_repr))
        return '<%s.%s at %s%s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)),
            ','.join(parts))

    def __getattr__(self, item):
        if item in ('form_values', 'form_errors'):
            warnings.warn('tmpl_context.form_values and tmpl_context.form_errors got deprecated '
                          'use request.validation instead', DeprecationWarning)
            return request.validation[item[5:]]
        elif item == 'controller_url':
            warnings.warn('tmpl_context.controller_url got deprecated, '
                          'use request.controller_url instead', DeprecationWarning)
            return request.controller_url

        raise AttributeError()


class AttribSafeContextObj(ContextObj):
    """The :term:`tmpl_context` object, with lax attribute access (
    returns '' when the attribute does not exist)"""
    def __getattr__(self, name):
        try:
            return ContextObj.__getattr__(self, name)
        except AttributeError:
            return ''
