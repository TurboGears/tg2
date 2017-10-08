# -*- coding: utf-8 -*-
import logging

from tg.configuration.configurator.steps.debugger import DebuggerConfigurationStep
from tg.configuration.configurator.steps.seekable_request import SeekableRequestConfigurationStep
from .minimal import MinimalApplicationConfigurator

from .steps.error_pages import ErrorPagesConfigurationStep
from .steps.error_reporting import ErrorReportingConfigurationStep
from .steps.ming import MingConfigurationStep
from .steps.slow_requests import SlowRequestsConfigurationStep
from .steps.sqlalchemy import SQLAlchemyConfigurationStep
from .steps.auth import SimpleAuthenticationConfigurationStep
from .steps.i18n import I18NConfigurationStep
from .steps.caching import CachingConfigurationStep
from .steps.session import SessionConfigurationStep
from .steps.toscawidgets2 import ToscaWidgets2ConfigurationStep
from .steps.statics import StaticsConfigurationStep

log = logging.getLogger(__name__)


class FullStackApplicationConfigurator(MinimalApplicationConfigurator):
    def __init__(self):
        super(FullStackApplicationConfigurator, self).__init__()
        self.update_blueprint({
            'use_dotted_templatenames': True,
        })

        self.register(I18NConfigurationStep)
        self.register(SimpleAuthenticationConfigurationStep)
        self.register(SessionConfigurationStep)
        self.register(CachingConfigurationStep)

        # from here on, due to TW2, the response is a generator
        # so any middleware that relies on the response to be
        # a string needs to be applied before this point.
        self.register(ToscaWidgets2ConfigurationStep)

        self.register(MingConfigurationStep)
        self.register(SQLAlchemyConfigurationStep)
        self.register(ErrorPagesConfigurationStep)

        self.register(SeekableRequestConfigurationStep)
        self.register(SlowRequestsConfigurationStep)
        self.register(ErrorReportingConfigurationStep)
        
        self.register(StaticsConfigurationStep)

        # Place the debuggers after the registry so that we
        # can preserve context in case of exceptions
        self.register(DebuggerConfigurationStep)
