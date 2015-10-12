# -*- coding: utf-8 -*-
from __future__ import absolute_import

try:
    from bson import ObjectId
except ImportError:  # pragma: no cover
    ObjectId = None

try:
    import ming
    import ming.odm
except ImportError:  # pragma: no cover
    ming = None


def is_objectid(value):
    return ObjectId is not None and isinstance(value, ObjectId)


def is_mingobject(obj):
    """Checks if the provided object is a Ming model instance"""
    return ming is not None and hasattr(obj, '__ming__')


def dictify(obj):
    """Converts a Ming model instance to a dictionary"""
    if ming is None:  # pragma: no cover
        raise RuntimeError("Ming is not available")

    prop_names = [prop.name for prop in ming.odm.mapper(obj).properties
                  if isinstance(prop, ming.odm.property.FieldProperty)]
    props = {}
    for key in prop_names:
        props[key] = getattr(obj, key)
    return props