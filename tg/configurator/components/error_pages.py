# -*- coding: utf-8 -*-
from tg.appwrappers.errorpage import ErrorPageApplicationWrapper
from ..base import ConfigurationComponent, BeforeConfigConfigurationAction


class ErrorPagesConfigurationComponent(ConfigurationComponent):
    """Provides support for custom error pages.

    This will enable the required parts to show a custom error page
    when a common HTTP error happens in the TurboGears application.

    Refer to :class:`.ErrorPageApplicationWrapper` for supported options.

    When simple authentication backend is set to ``None`` (auth disabled)
    status code ``401`` will always be handled by custom error pages
    even if not specified in ``errorpage.status_codes``.

    """
    id = 'error_pages'

    def get_defaults(self):
        return {
            'errorpage.enabled': True,
            'errorpage.status_codes': [403, 404]
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self._configure_error_pages),
        )

    def on_bind(self, configurator):
        configurator.register_application_wrapper(ErrorPageApplicationWrapper, after=True)

    def _configure_error_pages(self, conf, app):
        if conf.get('auth_backend') is None and 401 not in conf['errorpage.status_codes']:
            # If there's no auth backend configured which traps 401
            # responses we redirect those responses to a nicely
            # formatted error page
            conf['errorpage.status_codes'] = list(conf['errorpage.status_codes']) + [401]

