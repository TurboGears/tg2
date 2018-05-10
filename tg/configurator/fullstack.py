# -*- coding: utf-8 -*-
import logging

from .components.debugger import DebuggerConfigurationComponent
from .components.seekable_request import SeekableRequestConfigurationComponent
from .minimal import MinimalApplicationConfigurator

from .components.error_pages import ErrorPagesConfigurationComponent
from .components.error_reporting import ErrorReportingConfigurationComponent
from .components.ming import MingConfigurationComponent
from .components.slow_requests import SlowRequestsConfigurationComponent
from .components.sqlalchemy import SQLAlchemyConfigurationComponent
from .components.transactions import TransactionManagerConfigurationComponent
from .components.auth import SimpleAuthenticationConfigurationComponent
from .components.i18n import I18NConfigurationComponent
from .components.caching import CachingConfigurationComponent
from .components.session import SessionConfigurationComponent
from .components.toscawidgets2 import ToscaWidgets2ConfigurationComponent
from .components.statics import StaticsConfigurationComponent

log = logging.getLogger(__name__)


class FullStackApplicationConfigurator(MinimalApplicationConfigurator):
    """An ApplicationConfigurator that enables all TurboGears components.

    This is meant to create full stack applications or generally applications
    where most components are needed and some can be explicitly disabled.

    Enables all components from :class:`.MinimalApplicationConfigurator`
    plus:

        - I18N support
        - Authentication
        - Sessions
        - Caching
        - Widgets (ToscaWidgets2)
        - Databases (Ming and SQLAlchemy)
        - Transaction Manager
        - Custom Error Pages
        - Seekable Requests
        - Slow Requests Reporting
        - Errors Reporting
        - Static Files
        - Interactive Debugger

    """
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
        self.register(TransactionManagerConfigurationComponent)
        self.register(ErrorPagesConfigurationComponent)

        self.register(SeekableRequestConfigurationComponent)
        self.register(SlowRequestsConfigurationComponent)
        self.register(ErrorReportingConfigurationComponent)
        
        self.register(StaticsConfigurationComponent, after=True)

        # Place the debuggers after the registry so that we
        # can preserve context in case of exceptions
        self.register(DebuggerConfigurationComponent, after=True)
