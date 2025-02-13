# -*- coding: utf-8 -*-
import logging

from .components.auth import SimpleAuthenticationConfigurationComponent
from .components.caching import CachingConfigurationComponent
from .components.debugger import DebuggerConfigurationComponent
from .components.error_pages import ErrorPagesConfigurationComponent
from .components.error_reporting import ErrorReportingConfigurationComponent
from .components.i18n import I18NConfigurationComponent
from .components.ming import MingConfigurationComponent
from .components.seekable_request import SeekableRequestConfigurationComponent
from .components.session import SessionConfigurationComponent
from .components.slow_requests import SlowRequestsConfigurationComponent
from .components.sqlalchemy import SQLAlchemyConfigurationComponent
from .components.statics import StaticsConfigurationComponent
from .components.transactions import TransactionManagerConfigurationComponent
from .minimal import MinimalApplicationConfigurator

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
        self.update_blueprint(
            {
                "use_dotted_templatenames": True,
            }
        )

        self.register(I18NConfigurationComponent)
        self.register(SimpleAuthenticationConfigurationComponent)
        self.register(SessionConfigurationComponent)
        self.register(CachingConfigurationComponent)

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
