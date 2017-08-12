import logging
import sys
from ..configuration.utils import coerce_config
from ..support.converters import asbool, aslist, asint
from .base import ApplicationWrapper

log = logging.getLogger(__name__)


class ErrorPageApplicationWrapper(ApplicationWrapper):
    """Given an Application it intercepts the response code and shows a custom page.

    Supported options are:

        - ``errorpage.enabled``: Whenever the custom error page is enabled or not.
        - ``errorpage.status_codes``: List of HTTP errors that should be trapped.
          By default 403, 404, 500.
        - ``errorpage.content_types``: List of Content-Types for which the custom error
          page should be displayed. IE: ``["text/html"]``. An empty list means all.
          An entry with value ``None`` means no content type provided.
          Default is ``["text/html", None]``.
        - ``errorpage.handle_exceptions``: Whenever exceptions should be trapped and
          treated as a 500 error or not. By default this is ``True`` when ``debug=false``.
        - ``errorapge.path``: Path of the controller should be displayed in case of
          errors. By default ``/error/document``.
    """

    def __init__(self, handler, config):
        super(ErrorPageApplicationWrapper, self).__init__(handler, config)

        options = {
            'enabled': False,
            'status_codes': tuple(),
            'handle_exceptions': not asbool(config.get('debug', False)),
            'path': '/error/document',
            'content_types': ["text/html", None]
        }
        options.update(coerce_config(config, 'errorpage.',  {
            'enabled': asbool,
            'status_codes': aslist,
            'handle_exceptions': asbool,
            'content_types': aslist
        }))

        self.handle_error_enabled = options['enabled']
        self.handle_status_codes = set(asint(s) for s in options['status_codes'])
        self.handle_exceptions = options['handle_exceptions']
        self.handle_error_path = options['path']
        self.handle_content_types = options['content_types']

        if self.handle_exceptions and 500 not in self.handle_status_codes:
            self.handle_status_codes.add(500)

        log.debug('ErrorPageApplicationWrapper enabled: %s -> %s',
                  self.handle_error_enabled, options)

    @property
    def injected(self):
        return self.handle_error_enabled

    def __call__(self, controller, environ, context):
        try:
            resp = self.next_handler(controller, environ, context)
        except:
            if self.handle_exceptions is False:
                raise
            # Provide crash details to backlash
            environ['backlash.exc_environ'] = environ.copy()
            environ['backlash.exc_info'] = sys.exc_info()
            # Force response to a 500 Error, otherwise it will be a 200
            resp = context.response
            resp.status_code = 500

        if not environ.get('tg.status_code_redirect', True):
            # status_code_redirect disabled per this request
            return resp

        status_code = resp.status_code
        content_type = resp.content_type
        log.debug('ErrorPageApplicationWrapper response: %s -> %s @ %s',
                  environ['PATH_INFO'], status_code, content_type)
        if status_code in self.handle_status_codes and \
                (not self.handle_content_types or content_type in self.handle_content_types):
            environ['tg.original_request'] = context.request.copy()
            environ['tg.original_response'] = resp

            environ['PATH_INFO'] = self.handle_error_path
            log.debug('ErrorPageApplicationWrapper serving %s:%s',
                      controller, self.handle_error_path)
            resp = self.next_handler(controller, environ, context)

        return resp
