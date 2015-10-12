# -*- coding: utf-8 -*-
from __future__ import absolute_import

try:
    import sqlalchemy
    from sqlalchemy.engine import ResultProxy, RowProxy
except ImportError:  # pragma: no cover
    sqlalchemy = None
    ResultProxy = None
    RowProxy = None


def is_saobject(obj):
    """Checks if the provided object is a SQLAlchemy model instance"""
    return sqlalchemy is not None and hasattr(obj, '_sa_class_manager')


def is_query_result(values):
    return ResultProxy is not None and isinstance(values, ResultProxy)


def is_query_row(obj):
    return RowProxy is not None and isinstance(obj, RowProxy)


def dictify(obj):
    """Converts a SQLAlchemy model instance to a dictionary"""
    if sqlalchemy is None:  # pragma: no cover
        raise RuntimeError('SQLAlchemy not available')

    if sqlalchemy.inspect(obj).detached:
        raise ValueError("SQLAlchemy instance '%r' must be attached to a session." % obj)

    props = {}
    for key in obj.__dict__:
        if not key.startswith('_sa_'):
            props[key] = getattr(obj, key)
    return props


