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
    """An ApplicationConfigurator that enables minimum set of components.

    This is meant to create small self contained applications that
    might serve the purpose of simple JSON webservices or micro
    web applications.

    Enables components for:

        - mimetypes
        - load controllers and templates from paths
        - dispatch requests to a root controller
        - provide tg.app_globals
        - provide helpers in templates
        - support templates rendering
        - enable requests local registry for tg.request, tg.response, etc...

    """
    def __init__(self):
        super(MinimalApplicationConfigurator, self).__init__()

        self.register(MimeTypesConfigurationComponent, after=False)
        self.register(PathsConfigurationComponent, after=False)
        self.register(DispatchConfigurationComponent, after=False)
        self.register(AppGlobalsConfigurationComponent)
        self.register(HelpersConfigurationComponent)
        self.register(TemplateRenderingConfigurationComponent)
        self.register(RegistryConfigurationComponent, after=True)



