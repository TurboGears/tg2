# -*- coding: utf-8 -*-
import logging

from .application import ApplicationConfigurator

from .steps.mimetypes import MimeTypesConfigurationComponent
from .steps.paths import PathsConfigurationComponent
from .steps.app_globals import AppGlobalsConfigurationComponent
from .steps.helpers import HelpersConfigurationComponent
from .steps.dispatch import DispatchConfigurationComponent
from .steps.rendering import TemplateRenderingConfigurationComponent
from .steps.registry import RegistryConfigurationComponent

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



