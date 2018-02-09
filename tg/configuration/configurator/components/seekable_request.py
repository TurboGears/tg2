# -*- coding: utf-8 -*-
from ..base import ConfigurationComponent, AppReadyConfigurationAction


class SeekableRequestConfigurationComponent(ConfigurationComponent):
    """Make the request body seekable, so it can be read multiple times.

    """
    id = "seekable_request"

    def get_coercion(self):
        return {
            'make_body_seekable': bool
        }

    def get_defaults(self):
        return {
            'make_body_seekable': False
        }

    def get_actions(self):
        return (
            AppReadyConfigurationAction(self._add_middleware),
        )

    def _add_middleware(self, conf, app):
        if conf['make_body_seekable']:
            from tg.support.middlewares import SeekableRequestBodyMiddleware
            return SeekableRequestBodyMiddleware(app)
        return app
