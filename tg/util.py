"""
Utility functions for TurobGears
"""
from inspect import getargspec
from itertools import izip, islice
from operator import isSequenceType


def to_kw(func, args, kw, start=0):
    """Convert all applicable arguments to keyword arguments."""
    kw = kw.copy()
    argnames, defaults = getargspec(func)[::3]
    defaults = ensure_sequence(defaults)
    kv_pairs = izip(islice(argnames, start, len(argnames) - len(defaults)), args) 
    for k, v in kv_pairs: 
        kw[k] = v 
    return args[len(argnames)-len(defaults)-start:], kw

def from_kw(func, args, kw, start=0):
    """Extract named positional arguments from keyword arguments."""
    argnames, defaults = getargspec(func)[::3]
    defaults = ensure_sequence(defaults)
    newargs = [kw.pop(name) for name in islice(argnames, start,
               len(argnames) - len(defaults)) if name in kw]
    newargs.extend(args)
    return newargs, kw

def ensure_sequence(obj):
    """Construct a sequence from object."""
    if obj is None:
        return []
    elif isSequenceType(obj):
        return obj
    else:
        return [obj]

def get_project_meta(name):
    """get metadata"""
    import os
    for dirname in os.listdir("./"):
        if dirname.lower().endswith("egg-info"):
            fname = os.path.join(dirname, name)
            return fname

def get_project_name():
    """get project name"""
    pkg_info = get_project_meta('PKG-INFO')
    if pkg_info:
        name = list(open(pkg_info))[1][6:-1]
        return name.strip()