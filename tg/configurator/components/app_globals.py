# -*- coding: utf-8 -*-
from ..._compat import import_module
from ...util import DottedFileNameFinder, Bunch
from ..base import (ConfigurationComponent,
                    ConfigReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class AppGlobalsConfigurationComponent(ConfigurationComponent):
    """Enables the application global object.

    ``tg.app_globals`` is a global object always available in TG
    and shared across all requests and threads of the application.

    It's meant to keep around any value or method that all other
    parts of the application might depend on. As it's shared
    between all application threads and requests its content
    should be immutable or it will lead to race conditions.

    By default an instance of ``.lib.app_globals.Globals`` from
    within your application package is used. If it's not available
    an empty ``Bunch`` will be created instead.

    Provided options:

    * ``app_globals`` -> Factory or Class that should be used to create
      application global object instead of getting it from the application package.

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
