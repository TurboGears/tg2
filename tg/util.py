"""Utilities"""
from pkg_resources import resource_filename
import warnings
from functools import update_wrapper
from tg.configuration.utils import get_partial_dict


class DottedFileLocatorError(Exception): pass


class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return get_partial_dict(name, self, Bunch)

    __setattr__ = dict.__setitem__

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


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

    @classmethod
    def lookup(cls, name, extension='.html'):
        """Convenience method that permits to quickly get a file by dotted notation.

        Creates a :class:`.DottedFileNameFinder` and uses it to lookup the given file
        using dotted notation. As :class:`.DottedFileNameFinder` provides a lookup
        cache, using this method actually disables the cache as a new finder is created
        each time, for this reason if you have recurring lookups it's better to actually
        create a dotted filename finder and reuse it.

        """
        finder = cls()
        return finder.get_dotted_filename(name, extension)


def no_warn(f, *args, **kwargs):
    """Decorator that suppresses warnings inside the decorated function"""
    def _f(*args, **kwargs):
        warnings.simplefilter("ignore")
        f(*args, **kwargs)
        warnings.resetwarnings()
    return update_wrapper(_f, f)


class LazyString(object):
    """Behaves like a string, but no instance is created until the string is actually used.

    Takes a function which should be a string factory and a set of arguments to pass
    to the factory. Whenever the string is accessed or manipulated the factory is called
    to create the actual string. This is used mostly by lazy internationalization.

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
    """Decorator to return a lazy-evaluated version of the original

    Applying decorator to a function it will create a :class:`.LazyString`
    with the decorated function as factory.

    """
    def newfunc(*args, **kwargs):
        return LazyString(func, *args, **kwargs)
    newfunc.__name__ = 'lazy_%s' % func.__name__
    newfunc.__doc__ = 'Lazy-evaluated version of the %s function\n\n%s' % \
        (func.__name__, func.__doc__)
    return newfunc
