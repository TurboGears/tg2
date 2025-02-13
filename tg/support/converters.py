# (c) 2005 Ian Bicking and contributors; written for Paste (http://pythonpaste.org)
# Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
#
# Adapted to TurboGears 2.3
import logging
from string import Template


def asbool(obj):
    if isinstance(obj, str):
        obj = obj.strip().lower()
        if obj in ["true", "yes", "on", "y", "t", "1"]:
            return True
        elif obj in ["false", "no", "off", "n", "f", "0"]:
            return False
        else:
            raise ValueError("String is not true/false: %r" % obj)
    return bool(obj)


def asint(obj):
    try:
        return int(obj)
    except (TypeError, ValueError):
        raise ValueError("Bad integer value: %r" % obj)


def aslist(obj, sep=None, strip=True):
    if isinstance(obj, str):
        lst = obj.split(sep)
        if strip:
            lst = [v.strip() for v in lst]
        return lst
    elif isinstance(obj, (list, tuple)):
        return obj
    elif obj is None:
        return []
    else:
        return [obj]


def astemplate(obj):
    if isinstance(obj, Template):
        return obj

    if not isinstance(obj, str):
        raise ValueError("Templates must be strings")

    return Template(obj)


def aslogger(val):
    if isinstance(val, logging.Logger):
        return val

    if not isinstance(val, str):
        raise ValueError("Logger names must be strings")

    return logging.getLogger(val)
