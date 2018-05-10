# -*- coding: utf-8 -*-
from ...support.converters import asbool
from ..base import (ConfigurationComponent,
                    BeforeConfigConfigurationAction,
                    AppReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class StaticsConfigurationComponent(ConfigurationComponent):
    """Provide support for serving Static Files.

    In production, use Apache or another web server to serve static files.

        - ``serve_static``: Enable / Disable serving static files. **Can be set from .ini file**
        - ``paths.static_files``: Directory where the static files should be served from.
                                  Refer to :class:`.PathsConfigurationComponent` for configuration.
    """
    id = 'statics'

    def get_defaults(self):
        return {
            'serve_static': True
        }

    def get_coercion(self):
        return {
            'serve_static': asbool
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure),
            AppReadyConfigurationAction(self._add_middleware)
        )

    def _configure(self, conf, app):
        if not conf['paths']['static_files']:
            conf['serve_static'] = False

    def _add_middleware(self, conf, app):
        if not conf['serve_static']:
            return app

        from tg.support.statics import StaticsMiddleware
        return StaticsMiddleware(app, conf['paths']['static_files'])