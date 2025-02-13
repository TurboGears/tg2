"""Caching decorator, took as is from pylons"""

import tg

from .support import EmptyContext, NoDefault
from .support.converters import asbool
from .util.instance_method import im_class, im_func


class cached_property(object):
    """
    Works like python @property but the decorated function only gets
    executed once, successive accesses to the property will just
    return the value previously stored into the object.

    The ``@cached_property`` decorator can be executed within a
    provided context, for example to make the cached property
    thread safe a Lock can be provided::

        from threading import Lock
        from tg.caching import cached_property

        class MyClass(object):
            @cached_property
            def my_property(self):
                return 'Value!'
            my_property.context = Lock()

    """

    def __init__(self, func):
        self.__name__ = func.__name__
        self.__module__ = func.__module__
        self.__doc__ = func.__doc__
        self.func = func
        self.context = EmptyContext()

    def _get_value(self, obj):
        value = obj.__dict__.get(self.__name__, NoDefault)
        if value is NoDefault:
            value = self.func(obj)
            obj.__dict__[self.__name__] = value
        return value

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        with self.context:
            return self._get_value(obj)


def _cached_call(
    func,
    args,
    kwargs,
    namespace,
    cache_key,
    expire="never",
    type=None,
    starttime=None,
    cache_headers=("content-type", "content-length"),
    cache_response=True,
    cache_extra_args=None,
):
    """
    Optional arguments:

    ``key_func``
        Function used to genereate the cache key, the function name
        and class will be used as the base for the cache key. If None
        the ``func`` itself will be used. It's usually handy when
        creating caches for decorated functions, for which we want the
        cache key to be generated on the decorated function and not on
        the decorator.
    ``key_dict``
        Arguments used to generate the cache key, only the arguments
        listed into this dictionary will be used to generate the
        cache key together with the key_func.
    ``expire``
        Time in seconds before cache expires, or the string "never".
        Defaults to "never"
    ``type``
        Type of cache to use: dbm, memory, file, memcached, or None for
        Beaker's default
    ``cache_headers``
        A tuple of header names indicating response headers that
        will also be cached.
    ``invalidate_on_startup``
        If True, the cache will be invalidated each time the application
        starts or is restarted.
    ``cache_response``
        Determines whether the response at the time beaker_cache is used
        should be cached or not, defaults to True.

        .. note::
            When cache_response is set to False, the cache_headers
            argument is ignored as none of the response is cached.

    If cache.enabled is set to False in the .ini file, then cache is
    disabled globally.
    """

    tg_locals = tg.request.environ["tg.locals"]
    enabled = asbool(tg_locals.config.get("cache.enabled", True))

    if not enabled:
        return func(*args, **kwargs)

    cache_extra_args = cache_extra_args or {}

    if type:
        cache_extra_args["type"] = type

    cache_obj = getattr(tg_locals, "cache", None)
    if not cache_obj:  # pragma: no cover
        raise Exception("TurboGears Cache object not found, ensure cache.enabled=True")

    my_cache = cache_obj.get_cache(namespace, **cache_extra_args)

    if expire == "never":
        cache_expire = None
    else:
        cache_expire = expire

    def create_func():
        result = func(*args, **kwargs)
        glob_response = tg_locals.response
        headers = glob_response.headerlist
        status = glob_response.status
        full_response = dict(
            headers=headers, status=status, cookies=None, content=result
        )
        return full_response

    response = my_cache.get_value(
        cache_key, createfunc=create_func, expiretime=cache_expire, starttime=starttime
    )
    if cache_response:
        glob_response = tg_locals.response
        glob_response.headerlist = [
            header
            for header in response["headers"]
            if header[0].lower() in cache_headers
        ]
        glob_response.status = response["status"]

    return response["content"]


def create_cache_key(func, key_dict=None, self=None):
    """Get a cache namespace and key used by the beaker_cache decorator.

    Example::
        from tg import cache
        from tg.caching import create_cache_key
        namespace, key = create_cache_key(MyController.some_method)
        cache.get_cache(namespace).remove(key)

    """
    kls = None
    imfunc = im_func(func)
    if imfunc:
        kls = im_class(func)
        func = imfunc
        cache_key = func.__name__
    else:
        cache_key = func.__name__
    if key_dict:
        cache_key += " " + " ".join("%s=%s" % (k, v) for k, v in key_dict.items())

    if not kls and self:
        kls = getattr(self, "__class__", None)

    if kls:
        return "%s.%s" % (kls.__module__, kls.__name__), cache_key
    else:
        return func.__module__, cache_key
