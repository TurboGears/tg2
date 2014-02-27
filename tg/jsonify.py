"""JSON encoding functions."""

import datetime
import decimal
import types

from json import JSONEncoder

from webob.multidict import MultiDict
from tg._compat import string_type

class NotExistingImport:
    pass

try:
    import sqlalchemy
    from sqlalchemy.engine import ResultProxy, RowProxy
except ImportError: #pragma: no cover
    ResultProxy=NotExistingImport
    RowProxy=NotExistingImport

try:
    from bson import ObjectId
except ImportError: #pragma: no cover
    ObjectId=NotExistingImport

def is_saobject(obj):
    return hasattr(obj, '_sa_class_manager')

class JsonEncodeError(Exception):
    """JSON Encode error"""


class GenericJSON(JSONEncoder):
    """JSON Encoder class"""

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
        elif isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, MultiDict):
            return obj.mixed()
        elif isinstance(obj, types.GeneratorType):
            return list(obj)
        else:
            return JSONEncoder.default(self, obj)

try: #pragma: no cover
    from simplegeneric import generic

    _default = GenericJSON()

    @generic
    def jsonify(obj):
        return _default.default(obj)

    class GenericFunctionJSON(GenericJSON):
        """Generic Function JSON Encoder class."""

        def default(self, obj):
            return jsonify(obj)

    _instance = GenericFunctionJSON()
except ImportError:

    def jsonify(obj): #pragma: no cover
        raise ImportError('simplegeneric is not installed')

    _instance = GenericJSON()


# General encoding functions

def encode(obj):
    """Return a JSON string representation of a Python object."""
    if isinstance(obj, string_type):
        return _instance.encode(obj)

    try:
        value = obj['test']
    except TypeError:
        if not hasattr(obj, '__json__') and not is_saobject(obj):
            raise JsonEncodeError('Your Encoded object must be dict-like.')
    except:
        pass

    return _instance.encode(obj)


def encode_iter(obj):
    """Encode object, yielding each string representation as available."""
    return _instance.iterencode(obj)
