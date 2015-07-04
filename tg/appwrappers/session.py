import logging
import warnings
from ..support.converters import asbool
from .base import ApplicationWrapper

try:
    from beaker.session import Session, SessionObject
except ImportError:  # pragma: no cover
    SessionObject = None


log = logging.getLogger(__name__)


class SessionApplicationWrapper(ApplicationWrapper):
    """Provides the Session Support

    The Session Application Wrapper will make a lazy session instance
    available every request under the ``environ['beaker.session']`` key and
    inside TurboGears context as ``session``.

    Supported options which can be provided by config are:
        - ``session.enabled``: Whenever sessions are enabled or not.
        - Beaker Options prefixed with ``session.``, see
          https://beaker.readthedocs.org/en/latest/configuration.html#session-options

    """
    def __init__(self, handler, config):
        super(SessionApplicationWrapper, self).__init__(handler, config)

        if SessionObject is None:  # pragma: no cover
            log.debug('Beaker not available, session disabled')
            self.enabled = False
            return

        # Load up the default params
        self.options = dict(invalidate_corrupt=True, type=None,
                            data_dir=None, key='beaker.session.id',
                            timeout=None, secret=None, log_file=None)

        # Pull out any config args meant for beaker session. if there are any
        for key, val in config.items():
            if key.startswith('beaker.session.'):
                warnings.warn('Session options should start with session. '
                              'instead of baker.session.', DeprecationWarning, 2)
                self.options[key[15:]] = val
            elif key.startswith('session.'):
                self.options[key[8:]] = val

        # Coerce and validate session params
        from beaker.util import coerce_session_params
        coerce_session_params(self.options)

        self.enabled = asbool(self.options.pop('enabled', True))

        log.debug('Sessions enabled: %s -> %s',
                  self.enabled, self.options)

    @property
    def injected(self):
        return self.enabled

    def __call__(self, controller, environ, context):
        context.session = session = SessionObject(environ, **self.options)
        environ['beaker.session'] = session
        environ['beaker.get_session'] = self._get_session

        if 'paste.testing_variables' in environ:
            environ['paste.testing_variables']['session'] = session

        response = self.next_handler(controller, environ, context)

        if session.accessed():
            session.persist()
            session_headers = session.__dict__['_headers']
            if session_headers['set_cookie']:
                cookie = session_headers['cookie_out']
                if cookie:
                    response.headers.extend((('Set-cookie', cookie),))

        return response

    def _get_session(self, session_id=None):
        return Session({}, session_id, use_cookies=False, **self.options)
