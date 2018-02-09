# -*- coding: utf-8 -*-
import logging

from tg.support.converters import asbool
from ..base import ConfigurationComponent, AppReadyConfigurationAction

log = logging.getLogger(__name__)


class DebuggerConfigurationComponent(ConfigurationComponent):
    """If debug is enabled, this function will return the app wrapped in
    the BackLash debugger middleware which displays
    interactive debugging sessions when a traceback occurs.

    """

    id = "debugger"

    def get_defaults(self):
        return {
            'debug': False
        }

    def get_coercion(self):
        return {
            'debug': asbool
        }

    def get_actions(self):
        return (
            AppReadyConfigurationAction(self._add_middleware),
        )

    def _add_middleware(self, conf, app):
        if asbool(conf.get('debug')):
            try:
                import backlash
            except ImportError:  # pragma: no cover
                log.warning("backlash not installed, debug mode won't be available")
            else:
                return backlash.DebuggedApplication(
                    app, context_injectors=[_turbogears_backlash_context]
                )
        return app


def _turbogears_backlash_context(environ):
    tgl = environ.get('tg.locals')
    return {'request': getattr(tgl, 'request', None)}
