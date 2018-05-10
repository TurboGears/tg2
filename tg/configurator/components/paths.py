# -*- coding: utf-8 -*-
import os

from tg.util import Bunch
from ..base import ConfigurationComponent, BeforeConfigConfigurationAction


class PathsConfigurationComponent(ConfigurationComponent):
    """Configure application paths.

    States where the application is contained, where
    to load controllers from, templates from, static files
    and which is the application Python package.

    Options:

        * ``package``: The python package containing the web application.
        * ``paths``: A Dictionary of directories where templates, static files
                     and controllers can be found::

                        {
                            'controllers': 'my/path/to/controlllers',
                            'static_files': 'my/path/to/files',
                            'templates': ['list/of/paths/to/templates']
                        )
        * ``static_files``: An alias to ``paths['static_files']`` for convenience.
    """
    id = "paths"

    DEFAULT_PATHS = {
        'root': None,
        'controllers': None,
        'templates': ['.'],
        'static_files': None
    }

    def get_defaults(self):
        return {
            'paths': Bunch(),
            'package': None
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_paths),
            BeforeConfigConfigurationAction(self._configure_root_modules)
        )

    def _configure_paths(self, conf, app):
        try:
            package = conf['package'].__name__
        except (KeyError, AttributeError):
            package = None

        if package is not None:
            conf['package_name'] = conf['package'].__name__
        else:
            conf['package_name'] = None

        if package is None:
            # if we don't have a specified package (ES: we are in minimal mode)
            # we are unable to get paths from the package itself.
            paths = Bunch()
        else:
            root = os.path.dirname(os.path.abspath(conf['package'].__file__))
            paths = Bunch(
                root=root,
                controllers=os.path.join(root, 'controllers'),
                static_files=os.path.join(root, 'public'),
                templates=[os.path.join(root, 'templates')]
            )

        # If the user defined custom paths, then use them instead of the
        # default ones:
        paths.update(conf['paths'])

        # Ensure all paths are set, load default ones otherwise
        for key, val in self.DEFAULT_PATHS.items():
            paths.setdefault(key, val)

        conf['paths'] = paths

    def _configure_root_modules(self, conf, app):
        root_module_path = conf['paths']['root']
        if not root_module_path:
            return None

        base_controller_path = conf['paths']['controllers']
        controller_path = base_controller_path[len(root_module_path)+1:]
        root_controller_module = '.'.join([conf['package_name']] + controller_path.split(os.sep) + ['root'])
        conf['application_root_module'] = root_controller_module