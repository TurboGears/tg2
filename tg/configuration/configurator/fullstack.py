# -*- coding: utf-8 -*-
import logging

from tg.configuration.configurator.steps.debugger import DebuggerConfigurationComponent
from tg.configuration.configurator.steps.seekable_request import SeekableRequestConfigurationComponent
from .minimal import MinimalApplicationConfigurator

from .steps.error_pages import ErrorPagesConfigurationComponent
from .steps.error_reporting import ErrorReportingConfigurationComponent
from .steps.ming import MingConfigurationComponent
from .steps.slow_requests import SlowRequestsConfigurationComponent
from .steps.sqlalchemy import SQLAlchemyConfigurationComponent
from .steps.auth import SimpleAuthenticationConfigurationComponent
from .steps.i18n import I18NConfigurationComponent
from .steps.caching import CachingConfigurationComponent
from .steps.session import SessionConfigurationComponent
from .steps.toscawidgets2 import ToscaWidgets2ConfigurationComponent
from .steps.statics import StaticsConfigurationComponent

log = logging.getLogger(__name__)


class FullStackApplicationConfigurator(MinimalApplicationConfigurator):
    def __init__(self):
        super(FullStackApplicationConfigurator, self).__init__()
        self.update_blueprint({
            'use_dotted_templatenames': True,
        })

        self.register(I18NConfigurationComponent)
        self.register(SimpleAuthenticationConfigurationComponent)
        self.register(SessionConfigurationComponent)
        self.register(CachingConfigurationComponent)

        # from here on, due to TW2, the response is a generator
        # so any middleware that relies on the response to be
        # a string needs to be applied before this point.
        self.register(ToscaWidgets2ConfigurationComponent)

        self.register(MingConfigurationComponent)
        self.register(SQLAlchemyConfigurationComponent)
        self.register(ErrorPagesConfigurationComponent)

        self.register(SeekableRequestConfigurationComponent)
        self.register(SlowRequestsConfigurationComponent)
        self.register(ErrorReportingConfigurationComponent)
        
        self.register(StaticsConfigurationComponent, after=True)

        # Place the debuggers after the registry so that we
        # can preserve context in case of exceptions
        self.register(DebuggerConfigurationComponent, after=True)
