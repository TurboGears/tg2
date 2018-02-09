# -*- coding: utf-8 -*-
import logging

from .application import ApplicationConfigurator

from .components.mimetypes import MimeTypesConfigurationComponent
from .components.paths import PathsConfigurationComponent
from .components.app_globals import AppGlobalsConfigurationComponent
from .components.helpers import HelpersConfigurationComponent
from .components.dispatch import DispatchConfigurationComponent
from .components.rendering import TemplateRenderingConfigurationComponent
from .components.registry import RegistryConfigurationComponent

log = logging.getLogger(__name__)


class MinimalApplicationConfigurator(ApplicationConfigurator):
    def __init__(self):
        super(MinimalApplicationConfigurator, self).__init__()

        self.register(MimeTypesConfigurationComponent, after=False)
        self.register(PathsConfigurationComponent, after=False)
        self.register(DispatchConfigurationComponent, after=False)
        self.register(AppGlobalsConfigurationComponent)
        self.register(HelpersConfigurationComponent)
        self.register(TemplateRenderingConfigurationComponent)
        self.register(RegistryConfigurationComponent, after=True)



