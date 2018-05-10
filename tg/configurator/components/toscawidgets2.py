# -*- coding: utf-8 -*-
from tg.support.converters import asbool

from ...configuration.utils import TGConfigError
from ..base import (ConfigurationComponent,
                    BeforeConfigConfigurationAction, AppReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)


class ToscaWidgets2ConfigurationComponent(ConfigurationComponent):
    """Support for ToscaWidgets2 based Widgets, Forms and Resources.

    Options:

        * ``tw2.enabled``: Enable ToscaWidgets2 support.
                           For backward compatibility also ``prefer_toscawidgets2``
                           and ``use_toscawidgets2`` options are supported.
        * ``custom_tw2_config``: Additional TW2 Middleware options to provide.
                                 This should be a dictionary of options.

    Some options from other components influence TW2 behaviour too:

        * ``auto_reload_templates``: Enable autoreloading of Widgets templates.
        * ``debug``: Enable debug mode for TW2 (also injects debug resources).
        * ``default_renderer``: Rendering Engine used to render Widgets templates.
        * ``renderers``: Rendering engines that can be used to render Widgets templates.

    """
    id = 'tw2'

    def get_defaults(self):
        return {
            'tw2.enabled': False,
            'custom_tw2_config': {}
        }

    def get_coercion(self):
        return {
            'tw2.enabled': asbool,
            'prefer_toscawidgets2': asbool,
            'use_toscawidgets2': asbool
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure),
            AppReadyConfigurationAction(self._add_middleware),
        )

    def _configure(self, conf, app):
        prefer_tw2 = conf.get('prefer_toscawidgets2')
        use_tw2 = conf.get('use_toscawidgets2')
        if prefer_tw2 or use_tw2:
            # Backward compatibility with <=2.3 options.
            conf['tw2.enabled'] = True

    def _add_middleware(self, conf, app):
        """Configure the ToscaWidgets2 middleware"""
        if not conf['tw2.enabled']:
            return app

        from tw2.core.middleware import Config, TwMiddleware
        from tg.i18n import ugettext, get_lang

        available_renderers = set(conf.get('renderers', []))
        shared_engines = list(available_renderers & set(Config.preferred_rendering_engines))
        if not shared_engines:
            raise TGConfigError(
                'None of the configured rendering engines %s is supported '
                'by ToscaWidgets2, unable to configure ToscaWidgets.' % available_renderers
            )

        default_renderer = conf.get('default_renderer', None)
        if default_renderer in shared_engines:
            tw2_engines = [default_renderer] + shared_engines
            tw2_default_engine = default_renderer
        else:
            # If preferred rendering engine is not available in TW2, fallback to another one
            tw2_engines = shared_engines
            tw2_default_engine = shared_engines[0]

        default_tw2_config = dict(default_engine=tw2_default_engine,
                                  preferred_rendering_engines=tw2_engines,
                                  translator=ugettext,
                                  get_lang=lambda: get_lang(all=False),
                                  auto_reload_templates=conf.get('auto_reload_templates', False),
                                  controller_prefix='/tw2/controllers/',
                                  res_prefix='/tw2/resources/',
                                  debug=conf['debug'],
                                  rendering_extension_lookup={
                                       'mako': ['mak', 'mako'],
                                       'genshi': ['genshi', 'html'],
                                       'jinja': ['jinja', 'jinja2'],
                                       'kajiki': ['kajiki', 'xhtml', 'xml']
                                  })

        default_tw2_config.update(conf.get('custom_tw2_config', {}))
        app = TwMiddleware(app, **default_tw2_config)
        return app
