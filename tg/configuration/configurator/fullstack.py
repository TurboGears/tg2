# -*- coding: utf-8 -*-
import logging

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


        # Tosca HERE
        self.register(MingConfigurationStep)
        self.register(SQLAlchemyConfigurationStep)
        self.register(ErrorPagesConfigurationStep)

        # Seekable HERE
        self.register(SlowRequestsConfigurationStep)
        self.register(ErrorReportingConfigurationStep)
