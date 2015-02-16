import sys
import logging
from tg.configuration.utils import coerce_config
from tg._compat import reraise
from tg.support.converters import asbool, asint

log = logging.getLogger(__name__)


class MingApplicationWrapper(object):
    """Automatically flushes the Ming ODMSession.

    In case an exception raised during excution it won't flush the session and it will
    instead close it throwing away any change.

    Supported options which can be provided by config are:

        - ``tm.autoflush``: Whenever to flush session at end of request if no exceptions happened.

    """
    def __init__(self, handler, config):
        self._handler = handler

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

        log.debug('MingSessionFlush enabled: %s -> %s attempts',
                  self.enabled, options)

    def __call__(self, controller, environ, context):
        if self.enabled is False:
            return self._handler(controller, environ, context)

        session = self.ThreadLocalODMSession

        try:
            resp = self._handler(controller, environ, context)
        except:
            session.close_all()
            raise

        log.debug('MingSessionFlush flushing changes...')
        session.flush_all()
        return resp
