"""Utilities"""
from pylons import config
import os, sys
import pkg_resources

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
        return AttributeError

class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __getitem__(self, key):
        return  dict.__getitem__(self, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return get_partial_dict(name, self)
            #if both getitem, and partial-dict matches fail we're done
            raise AttributeError(name)

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
