"""JSON encoding functions using EAK-Rules."""

import datetime
import decimal

from simplejson import JSONEncoder

import sqlalchemy

def is_saobject(obj):
    return hasattr(obj, '_sa_class_manager')

from sqlalchemy.engine.base import ResultProxy, RowProxy


# JSON Encoder class

class GenericJSON(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__json__'):
            return obj.__json__()
        elif isinstance(obj, (datetime.date, datetime.datetime)):
            return str(obj)
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif is_saobject(obj):
            props = {}
            for key in obj.__dict__:
                if not key.startswith('_sa_'):
                    props[key] = getattr(obj, key)
            return props
        elif isinstance(obj, ResultProxy):
            return list(obj)
        elif isinstance(obj, RowProxy):
            return dict(obj)
        else:
            return JSONEncoder.default(self, obj)

_instance = GenericJSON()


# General encoding functions

def encode(obj):
    """Return a JSON string representation of a Python object."""
    return _instance.encode(obj)

def encode_iter(obj):
    """Encode object, yielding each string representation as available."""
    return _instance.iterencode(obj)
