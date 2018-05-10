# -*- coding: utf-8 -*-
import copy

from tg.configuration import milestones
from tg.configuration.utils import TGConfigError
from tg.support.converters import asbool
from ..base import (ConfigurationComponent, BeforeConfigConfigurationAction,
                    ConfigReadyConfigurationAction)

from logging import getLogger
log = getLogger(__name__)

__all__ = ('TemplateRenderingConfigurationComponent', )


class TemplateRenderingConfigurationComponent(ConfigurationComponent):
    """Provides support for rendering engines.

    The available options are:

        - ``use_dotted_templatenames`` -> (``True``/``False``) Use template names as packages in
          @expose instead of file paths. This is usually the default unless TG is started
          in Minimal Mode.
        - ``auto_reload_templates`` -> (``True``/``False``) Automatically reload template files
          if they change. Should usually be disabled on production for performance reasons.
        - ``tg.strict_tmpl_context`` -> (``True``/``False``) Should ``tg.tmpl_context`` be
          strict and complain about missing value or should it always just return empty values
          for missing ones?
        - ``renderers`` -> (``list(str)``) List of template engines that should be enabled.
        - ``default_renderer`` -> (``str``) The default template engine to use when not explicitly
          specified by ``@expose`` decorations.

    Refer to each template engine renderer for specific configuration options.
    """
    id = 'rendering'

    def __init__(self):
        super(TemplateRenderingConfigurationComponent, self).__init__()
        self.rendering_engines = {}
        self.rendering_engines_options = {}
        self.rendering_engines_without_vars = set()

    def get_coercion(self):
        return {
            'auto_reload_templates': asbool,
            'use_dotted_templatenames': asbool,
            'tg.strict_tmpl_context': asbool,
        }

    def get_defaults(self):
        return {
            'tg.strict_tmpl_context': True,
            'auto_reload_templates': True,
            'use_dotted_templatenames': False,
            'renderers': [],
            'default_renderer': 'kajiki',
            'render_functions': {},
            'rendering_engines': {},
            'rendering_engines_without_vars': set(),
            'rendering_engines_options': {}
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_rendering),
            ConfigReadyConfigurationAction(self._setup_renderers)
        )

    def on_bind(self, configurator):
        from ...renderers.json import JSONRenderer
        from ...renderers.genshi import GenshiRenderer
        from ...renderers.jinja import JinjaRenderer
        from ...renderers.kajiki import KajikiRenderer
        from ...renderers.mako import MakoRenderer

        self.register_engine(JSONRenderer)
        self.register_engine(GenshiRenderer)
        self.register_engine(MakoRenderer)
        self.register_engine(JinjaRenderer)
        self.register_engine(KajikiRenderer)

    def register_engine(self, factory):
        """Registers a rendering engine ``factory``.

        Rendering engine factories are :class:`tg.renderers.base.RendererFactory`
        subclasses in charge of creating a rendering engine.

        """
        for engine, options in factory.engines.items():
            self.rendering_engines[engine] = factory
            self.rendering_engines_options[engine] = options
            if factory.with_tg_vars is False:
                self.rendering_engines_without_vars.add(engine)

    def _configure_rendering(self, conf, app):
        """Provides default configurations for renderers"""
        if 'json' not in conf['renderers']:
            conf['renderers'].append('json')

        if conf['default_renderer'] not in conf['renderers']:
            first_renderer = conf['renderers'][0]
            log.warning('Default renderer not in renders, '
                        'automatically switching to %s' % first_renderer)
            conf['default_renderer'] = first_renderer

        conf['rendering_engines'] = copy.copy(self.rendering_engines)
        conf['rendering_engines_options'] = copy.copy(self.rendering_engines_options)
        conf['rendering_engines_without_vars'] = copy.copy(self.rendering_engines_without_vars)

    def _setup_renderers(self, conf, app):
        renderers = conf['renderers']
        rendering_engines = conf['rendering_engines']

        for renderer in renderers[:]:
            if renderer in rendering_engines:
                rendering_engine = rendering_engines[renderer]
                engines = rendering_engine.create(conf, conf['tg.app_globals'])
                if engines is None:
                    log.error('Failed to initialize %s template engine, removing it...' % renderer)
                    renderers.remove(renderer)
                else:
                    log.debug('Enabling renderer %s', renderer)
                    conf['render_functions'].update(engines)
            else:
                raise TGConfigError('This configuration object does '
                                    'not support the %s renderer' % renderer)

        milestones.renderers_ready.reach()