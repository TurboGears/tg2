# -*- coding: utf-8 -*-
from tg.support.converters import asbool
from ..base import ConfigurationComponent, AppReadyConfigurationAction


class SeekableRequestConfigurationComponent(ConfigurationComponent):
    """Support for making the request body seekable.

    This allows to make the request body seekable, so that it can be
    read multiple times and it's possible to go back and forth in
    request submitted data. Note that this has a cost in terms of
    consumed memory.

    Options:

        * ``make_body_seekable``: Enable seekable request body.
                                  By default this is disabled.

    """
    id = "seekable_request"

    def get_coercion(self):
        return {
            'make_body_seekable': asbool
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
