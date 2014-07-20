"""JSON encoding functions."""

import datetime
import decimal
import types

from json import JSONEncoder as _JSONEncoder

from webob.multidict import MultiDict
from tg._compat import string_type
import logging

log = logging.getLogger(__name__)


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

try:
    import ming
    import ming.odm
except ImportError: #pragma: no cover
    ming=NotExistingImport

def is_saobject(obj):
    return hasattr(obj, '_sa_class_manager')

def is_mingobject(obj):
    return hasattr(obj, '__ming__')


class JsonEncodeError(Exception):
    """JSON Encode error"""


class JSONEncoder(_JSONEncoder):
    """JSON Encoder class"""

    def __init__(self, **kwargs):
        self._registered_types_map = {}
        self._registered_types_list = tuple()

        kwargs = self.configure(**kwargs)
        super(JSONEncoder, self).__init__(**kwargs)

    def configure(self, isodates=False, custom_encoders=None, **kwargs):
        self._isodates = isodates
        if custom_encoders is not None:
            for type_, encoder in custom_encoders.items():
                self.register_custom_encoder(type_, encoder)
        return kwargs

    def register_custom_encoder(self, objtype, encoder):
        if objtype in self._registered_types_map:
            log.warning('%s type already registered for a custom encoder, replacing it', objtype)

        self._registered_types_map[objtype] = encoder
        # Append to head, so we find first the last registered types
        self._registered_types_list = (objtype, ) + self._registered_types_list

    def default(self, obj):
        if isinstance(obj, self._registered_types_list):
            # Minor optimization, enter loop only when we are instance of a supported type.
            for type_, encoder in self._registered_types_map.items():
                if isinstance(obj, type_):
                    return encoder(obj)
        elif hasattr(obj, '__json__') and callable(obj.__json__):
            return obj.__json__()
        elif isinstance(obj, (datetime.date, datetime.datetime)):
            if self._isodates:
                return obj.replace(microsecond=0).isoformat()
            else:
                return str(obj)
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif is_saobject(obj):
            props = {}
            for key in obj.__dict__:
                if not key.startswith('_sa_'):
                    props[key] = getattr(obj, key)
            return props
        elif is_mingobject(obj) and ming is not NotExistingImport:
            prop_names = [prop.name for prop in ming.odm.mapper(obj).properties
                          if isinstance(prop, ming.odm.property.FieldProperty)]

            props = {}
            for key in prop_names:
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
            return _JSONEncoder.default(self, obj)


_default_encoder = JSONEncoder()


def encode(obj, encoder=None, iterencode=False):
    """Return a JSON string representation of a Python object."""
    if encoder is None:
        encoder = _default_encoder

    encode_func = encoder.encode
    if iterencode:
        encode_func = encoder.iterencode

    if isinstance(obj, string_type):
        return encode_func(obj)

    try:
        value = obj['test']
    except TypeError:
        if not hasattr(obj, '__json__') and not is_saobject(obj):
            raise JsonEncodeError('Your Encoded object must be dict-like.')
    except:
        pass

    return encode_func(obj)


def encode_iter(obj, encoder=None):
    """Encode object, yielding each string representation as available."""
    return encode(obj, encoder=encoder, iterencode=True)
