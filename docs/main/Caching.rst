Caching in TurboGears 2
=================================

There are three forms of caching supported by Pylons, and therefore TurboGears 2.

Here are some brief examples of how to use the various forms of cache available.

Arbitrary caching within controllers
------------------------------------------

Caches have names, and within caches values are identified by a key.  Each cache for each key has a creation function, which is called to regenerate the value for that cache key.  When the value expires, a new value is generated.

The creation function is unparameterized, and cannot be a closure within your controller function, because it is bound only once, on creation of the cache::

    from pylons import cache
    from tg.controllers import TurboGearsController

    class Example(TurboGearsController):

        def _expensive(self):
            # do something expensive
            return value
    
        @expose()
        def index(self):
            c = cache.get_cache("example_cache")
            x = c.get_value(key="my key", 
                            createfunc=self._expensive,
                            type="memory",
                            expiretime=3600)

Using the cache decorator
-------------------------------

This caches the output of controllers - effectively a form of Memoization.  
The cache is keyed on the arguments passed, or optionally on the request itself::

    from pylons.decorators.cache import beaker_cache
    from tg.controllers import TurboGearsController

    class SampleController(TurboGearsController):

        # Cache this controller action forever (until the cache dir 
        # is cleaned)
        @beaker_cache()
        def home(self):
            c.data = expensive_call()
            return "foo"

        # Cache this controller action by its GET args for 10 mins to memory
        @beaker_cache(expire=600, type='memory', query_args=True)
        def show(self, id):
            c.data = expensive_call(id)
            return "foo"

Using the ETag cache
===========================

This is just a shorthand for setting the ETag header, and testing if the 
appropriate '''If-None-Match''' HTTP Header has been set::


    from pylons.controllers.util import etag_cache
    from tg.controllers import TurboGearsController

    class SampleController(TurboGearsController):

        def my_action(self):
            etag_cache('somekey')
            ...

