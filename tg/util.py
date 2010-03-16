"""Utilities"""
import os, sys
import pkg_resources
from pkg_resources import resource_filename
import warnings

from pylons.configuration import config


class DottedFileLocatorError(Exception):pass

def get_project_meta(name):
    for dirname in os.listdir("./"):
        if dirname.lower().endswith("egg-info"):
            fname = os.path.join(dirname, name)
            return fname

def get_project_name():
    """get project name if exist"""
    pkg_info = get_project_meta('PKG-INFO')
    if pkg_info:
        name = list(open(pkg_info))[1][6:-1]
        return name.strip()

def get_package_name():
    """Try to find out the package name of the current directory."""
    package = config.get("modules")
    if package:
        return package

    if "--egg" in sys.argv:
        projectname = sys.argv[sys.argv.index("--egg")+1]
        egg = pkg_resources.get_distribution(projectname)
        top_level = egg._get_metadata("top_level.txt")
    else:
        fname = get_project_meta('top_level.txt')
        top_level = fname and open(fname) or []

    for package in top_level:
        package = package.rstrip()
        if package and package != 'locales':
            return package

def get_model():
    """return model"""
    package_name = get_package_name()

    if not package_name:
        return None

    package = __import__(package_name, {}, {}, ["model"])

    if hasattr(package, "model"):
        return package.model

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
                       for key in dictionary.iterkeys()
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
        if template_name.startswith('app:'):
            template_name = '.'.join((get_package_name(), template_name[4:]))
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
                except ImportError, e:
                    raise DottedFileLocatorError(e.message +". Perhaps you have forgotten an __init__.py in that folder.")
            else:
                result = template_name

            self.__cache[template_name] = result

            return result

class odict(dict):

    def __init__(self, *args, **kw):
        self._ordering = []
        dict.__init__(self, *args, **kw)

    def __setitem__(self, key, value):
        if key in self._ordering:
            self._ordering.remove(key)
        self._ordering.append(key)
        dict.__setitem__(self, key, value)

    def keys(self):
        return self._ordering

    def clear(self):
        self._ordering = []
        dict.clear(self)

    def getitem(self, n):
        return self[self._ordering[n]]
        

#    def __slice__(self, a, b=-1, n=1):
#        return self.values()[a:b:n]

    def iteritems(self):
        for item in self._ordering:
            yield item, self[item]

    def items(self):
        return [i for i in self.iteritems()]

    def itervalues(self):
        for item in self._ordering:
            yield self[item]

    def values(self):
        return [i for i in self.itervalues()]

    def __delitem__(self, key):
        self._ordering.remove(key)
        dict.__delitem__(self, key)

    def pop(self):
        item = self._ordering[-1]
        del self[item]

    def __str__(self):
        return str(self.items())

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