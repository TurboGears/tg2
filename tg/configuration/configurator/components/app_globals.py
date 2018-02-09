# -*- coding: utf-8 -*-
from ...._compat import import_module
from ....util import DottedFileNameFinder, Bunch
from ..base import (ConfigurationComponent,
                    ConfigReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class AppGlobalsConfigurationComponent(ConfigurationComponent):
    """

    """
    id = 'app_globals'

    def get_defaults(self):
        return {
            'app_globals': None,
        }

    def get_actions(self):
        return (
            ConfigReadyConfigurationAction(self._setup_app_globals),
        )

    def _setup_app_globals(self, conf, app):
        """Add helpers and globals objects to the ``conf``.

        Override this method to customize the way that ``app_globals`` and ``helpers``
        are setup. TurboGears expects them to be available in ``conf`` dictionary
        as ``tg.app_globals`` and ``helpers``.
        """
        # Setup AppGlobals
        gclass = conf.pop('app_globals', None)
        if gclass is None:
            try:
                gclass = conf['package'].lib.app_globals.Globals
            except AttributeError:
                pass

        if gclass is None:
            try:
                app_globals_mod = import_module('.lib.app_globals',
                                                package=conf['package'].__name__)
                gclass = getattr(app_globals_mod, 'Globals')
            except (ImportError, AttributeError):
                pass

        if gclass is None:
            log.warning('app_globals not provided and lib.app_globals.Globals is not available.')
            gclass = Bunch

        g = gclass()

        g.dotted_filename_finder = DottedFileNameFinder()
        conf['tg.app_globals'] = g
