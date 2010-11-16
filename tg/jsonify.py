"""JSON encoding functions using EAK-Rules."""

import datetime
import decimal

from simplejson import JSONEncoder

try:
    import sqlalchemy
    from sqlalchemy.engine.base import ResultProxy, RowProxy
except ImportError:
    ResultProxy=None
    RowProxy=None

def is_saobject(obj):
    return hasattr(obj, '_sa_class_manager')

from webob.multidict import MultiDict

class JsonEncodeError(Exception):pass

# JSON Encoder class
class GenericJSON(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, '__json__') and callable(obj.__json__):
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
            return dict(rows=list(obj), count=obj.rowcount)
        elif isinstance(obj, RowProxy):
            return dict(rows=dict(obj), count=1)
        elif isinstance(obj, MultiDict):
            return obj.mixed()
        else:
            return JSONEncoder.default(self, obj)

# Generic Function JSON Encoder class

try:
    from simplegeneric import generic

    _default = GenericJSON()

    @generic
    def jsonify(obj):
        return _default.default(obj)

    class GenericFunctionJSON(GenericJSON):
        def default(self, obj):
            return jsonify(obj)

    _instance = GenericFunctionJSON()
except ImportError:
    _instance = GenericJSON()

# General encoding functions

def encode(obj):
    if isinstance(obj, basestring):
        return _instance.encode(obj)
    try:
        value = obj['test']
    except TypeError:
        if not hasattr(obj, '__json__') and not is_saobject(obj):
            raise JsonEncodeError('Your Encoded object must be dict-like.')
    except:
        pass
    """Return a JSON string representation of a Python object."""
    return _instance.encode(obj)

def encode_iter(obj):
    """Encode object, yielding each string representation as available."""
    return _instance.iterencode(obj)
