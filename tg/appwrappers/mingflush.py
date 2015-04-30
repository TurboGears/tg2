import logging
from tg.configuration.utils import coerce_config
from tg.support.converters import asbool, asint
from .base import ApplicationWrapper

log = logging.getLogger(__name__)


class MingApplicationWrapper(ApplicationWrapper):
    """Automatically flushes the Ming ODMSession.

    In case an exception raised during excution it won't flush the session and it will
    instead close it throwing away any change.

    Supported options which can be provided by config are:

        - ``ming.autoflush``: Whenever to flush session at end of request if no exceptions happened.

    """
    def __init__(self, handler, config):
        super(MingApplicationWrapper, self).__init__(handler, config)

        options = {
            'autoflush': False,
        }
        options.update(coerce_config(config, 'ming.',  {
            'autoflush': asbool,
        }))

        self.ThreadLocalODMSession = None
        self.enabled = options['autoflush']

        if self.enabled:
            try:
                from ming.odm import ThreadLocalODMSession
                self.ThreadLocalODMSession = ThreadLocalODMSession
            except ImportError:  # pragma: no cover
                log.exception('Unable to Enable Ming Application Wrapper')
                self.enabled = False

        log.debug('MingSessionFlush enabled: %s -> %s',
                  self.enabled, options)

    @property
    def injected(self):
        return self.enabled

    def __call__(self, controller, environ, context):
        session = self.ThreadLocalODMSession

        try:
            resp = self.next_handler(controller, environ, context)
        except:
            session.close_all()
            raise

        log.debug('MingSessionFlush flushing changes...')
        session.flush_all()
        return resp
