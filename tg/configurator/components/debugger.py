# -*- coding: utf-8 -*-
import logging

from tg.support.converters import asbool
from ..base import ConfigurationComponent, AppReadyConfigurationAction

log = logging.getLogger(__name__)


class DebuggerConfigurationComponent(ConfigurationComponent):
    """Enabled Backlash interactive debugger support.

    If debug is enabled, the TurboGears app will be wrapped in
    the BackLash debugger middleware which displays
    interactive debugging sessions when a traceback occurs.

    Supported Options:

        * ``debug``: Whenever to enable or not the interactive debugger.

    Make sure that the interactive debugger is never enable on
    production, or it will be a major security issue as it will
    allow full remote code execution.
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
