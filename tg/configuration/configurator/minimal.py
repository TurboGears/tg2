# -*- coding: utf-8 -*-
import logging

from .application import ApplicationConfigurator

from .steps.mimetypes import MimeTypesConfigurationStep
from .steps.paths import PathsConfigurationStep
from .steps.app_globals import AppGlobalsConfigurationStep
from .steps.helpers import HelpersConfigurationStep
from .steps.dispatch import DispatchConfigurationStep
from .steps.rendering import TemplateRenderingConfigurationStep
from .steps.registry import RegistryConfigurationStep

log = logging.getLogger(__name__)


class MinimalApplicationConfigurator(ApplicationConfigurator):
    def __init__(self):
        super(MinimalApplicationConfigurator, self).__init__()

        self.register(MimeTypesConfigurationStep, after=False)
        self.register(PathsConfigurationStep, after=False)
        self.register(DispatchConfigurationStep, after=False)
        self.register(AppGlobalsConfigurationStep)
        self.register(HelpersConfigurationStep)
        self.register(TemplateRenderingConfigurationStep)
        self.register(RegistryConfigurationStep, after=True)



