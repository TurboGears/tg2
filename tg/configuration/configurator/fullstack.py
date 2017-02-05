# -*- coding: utf-8 -*-
import logging

from .minimal import MinimalApplicationConfigurator

from .steps.error_pages import ErrorPagesConfigurationStep
from .steps.error_reporting import ErrorReportingConfigurationStep
from .steps.ming import MingConfigurationStep
from .steps.slow_requests import SlowRequestsConfigurationStep
from .steps.sqlalchemy import SQLAlchemyConfigurationStep

log = logging.getLogger(__name__)


class FullStackApplicationConfigurator(MinimalApplicationConfigurator):
    def __init__(self):
        super(FullStackApplicationConfigurator, self).__init__()
        self.update_blueprint({
            'use_dotted_templatenames': True,
        })

        self.register(ErrorPagesConfigurationStep)
        self.register(SQLAlchemyConfigurationStep)
        self.register(MingConfigurationStep)
        self.register(ErrorReportingConfigurationStep)
        self.register(SlowRequestsConfigurationStep)
