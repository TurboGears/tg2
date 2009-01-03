"""Utilities"""
from pylons import config
import os, sys
import pkg_resources
import urlparse
from pkg_resources import resource_filename

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

    new_dict = Bunch([(key.lstrip(match) ,dictionary[key]) 
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

def get_dotted_filename(template_name, template_extension='.html'):
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
    divider = template_name.rfind('.')
    if divider >= 0:
        package = template_name[:divider]
        basename = template_name[divider + 1:] + template_extension
        result = resource_filename(package, basename)

    else:
        result = template_name

    return result


# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]

def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):

        uri = "".join([encode(c) for c in uri]).encode('utf8')
    return uri