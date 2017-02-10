# -*- coding: utf-8 -*-
import logging

from .minimal import MinimalApplicationConfigurator

from .steps.error_pages import ErrorPagesConfigurationStep
from .steps.error_reporting import ErrorReportingConfigurationStep
from .steps.ming import MingConfigurationStep
from .steps.slow_requests import SlowRequestsConfigurationStep
from .steps.sqlalchemy import SQLAlchemyConfigurationStep

from ...appwrappers.i18n import I18NApplicationWrapper
from ...appwrappers.identity import IdentityApplicationWrapper
from ...appwrappers.caching import CacheApplicationWrapper
from ...appwrappers.mingflush import MingApplicationWrapper
from ...appwrappers.session import SessionApplicationWrapper
from ...appwrappers.transaction_manager import TransactionApplicationWrapper

log = logging.getLogger(__name__)


class FullStackApplicationConfigurator(MinimalApplicationConfigurator):
    def __init__(self):
        super(FullStackApplicationConfigurator, self).__init__()
        self.update_blueprint({
            'use_dotted_templatenames': True,
        })

        self.register(ErrorPagesConfigurationStep)
        # Tosca HERE
        self.register(SQLAlchemyConfigurationStep)
        self.register(MingConfigurationStep)
        # Seekable HERE
        self.register(ErrorReportingConfigurationStep)
        self.register(SlowRequestsConfigurationStep)

        self.register_application_wrapper(I18NApplicationWrapper, after=True)
        self.register_application_wrapper(IdentityApplicationWrapper, after=True)
        self.register_application_wrapper(SessionApplicationWrapper, after=True)
        self.register_application_wrapper(CacheApplicationWrapper, after=True)
        self.register_application_wrapper(MingApplicationWrapper, after=True)
        self.register_application_wrapper(TransactionApplicationWrapper, after=True)
