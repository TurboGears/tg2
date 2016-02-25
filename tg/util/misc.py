# -*- coding: utf-8 -*-
from functools import wraps


def unless(func, check=None):
    """Wraps ``func`` ensuring it returns a value different from ``check``.

    A new function that calls ``func`` and checks its value is returned.
    In case func returns a value equal to check a ``ValueError`` is
    raised.

    A common usage pattern is to join this with  :class:`.Convert`
    to fail validation when querying objects from the database
    if they do not exist::

        Convert(unless(DBSession.query(User).get))

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        v = func(*args, **kwargs)
        if v == check:
            raise ValueError('{} == {}'.format(v, check))
        return v
    return wrapper

