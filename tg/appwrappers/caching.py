import logging
from ..support.converters import asbool
from .base import ApplicationWrapper

try:
    from beaker.cache import CacheManager
except ImportError:  # pragma: no cover
    CacheManager = None


log = logging.getLogger(__name__)


class CacheApplicationWrapper(ApplicationWrapper):
    """Provides Caching Support.

    The Cache Application Wrapper will make a CacheManager instance available
    every request under the ``environ['beaker.cache']`` key and inside the
    TurboGears request context as ``cache``.

    Supported options which can be provided by config are:
        - ``cache.enabled``: Whenever caching is enabled or not.
        - Beaker Options prefixed with ``cache.``, see
          https://beaker.readthedocs.org/en/latest/configuration.html#cache-options

    """
    def __init__(self, handler, config):
        super(CacheApplicationWrapper, self).__init__(handler, config)

        if CacheManager is None:  # pragma: no cover
            self.enabled = False
            log.debug('Beaker not available, caching disabled')
            return

        from beaker.util import parse_cache_config_options
        self.options = parse_cache_config_options(config)

        self.cache_manager = CacheManager(**self.options)
        self.enabled = asbool(self.options.pop('enabled', True))

        log.debug('Caching enabled: %s -> %s',
                  self.enabled, self.options)

    @property
    def injected(self):
        return self.enabled

    def __call__(self, controller, environ, context):
        environ['beaker.cache'] = context.cache = self.cache_manager

        if 'paste.testing_variables' in environ:
            environ['paste.testing_variables']['cache'] = context.cache

        return self.next_handler(controller, environ, context)
