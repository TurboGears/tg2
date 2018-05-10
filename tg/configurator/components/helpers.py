# -*- coding: utf-8 -*-
from ...util import Bunch
from ..._compat import import_module
from ..base import (ConfigurationComponent,
                    ConfigReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class HelpersConfigurationComponent(ConfigurationComponent):
    """Add support for helpers in templates.

    Helpers are a bunch of help functions, usually involved
    in generating small HTML snippets or formatting data
    that are exposed in templates under the ``h`` object.

    By default the helpers will be loaded from your application
    package as ``package.lib.helpers`` which is expected
    to be a module containing all helpers functions.

    Supported options:

        * ``helpers``: Set a different object as the template helpers.

    """
    id = 'helpers'

    def get_defaults(self):
        return {
            'helpers': None,
        }

    def get_actions(self):
        return (
            ConfigReadyConfigurationAction(self._setup_helpers),
        )

    def _setup_helpers(self, conf, app):
        """Add helpers and globals objects to the ``conf``.

        Override this method to customize the way that ``app_globals`` and ``helpers``
        are setup. TurboGears expects them to be available in ``conf`` dictionary
        as ``tg.app_globals`` and ``helpers``.
        """
        # Setup Helpers
        h = conf.get('helpers', None)
        if h is None:
            try:
                h = conf['package'].lib.helpers
            except AttributeError:
                pass

        if h is None:
            try:
                h = import_module('.lib.helpers', package=conf['package'].__name__)
            except (ImportError, AttributeError):
                pass

        if h is None:
            log.warning('helpers not provided and lib.helpers is not available.')
            h = Bunch()

        conf['helpers'] = h


