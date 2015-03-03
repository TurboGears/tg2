import sys
import logging
from ..configuration.utils import coerce_config
from .._compat import reraise
from ..support.converters import asbool, asint
from .base import ApplicationWrapper

log = logging.getLogger(__name__)


class AbortTransaction(Exception):
    def __init__(self, response):
        self.response = response


class TransactionApplicationWrapper(ApplicationWrapper):
    """Wraps the whole application in zope.transaction transaction manager and
    rollbacks transaction in case of crashes.

    Supported options which can be provided by config are:

        - ``tm.enabled``: Wenever the transaction manager is enabled or not.
        - ``tm.attempts``: Number of times the transaction should be retried if
          it fails (no retry by default)
        - ``tm.commit_veto``: A function that will be called for every transaction to check
          if it should abort transaction or let it go. Function signature shoul be:
          ``function(environ, status_code, headers) -> bool``.

    """
    def __init__(self, handler, config):
        super(TransactionApplicationWrapper, self).__init__(handler, config)

        options = {
            'enabled': False,
            'attempts': 1,
            'commit_veto': None
        }
        options.update(coerce_config(config, 'tm.',  {
            'enabled': asbool,
            'attempts': asint,
        }))

        self.enabled = options['enabled']
        self.attempts = options['attempts']
        self.commit_veto = options['commit_veto']
        self.manager = None

        if self.enabled:
            try:
                import transaction
                self.manager = transaction.manager
            except ImportError:  # pragma: no cover
                log.exception('Unable to Enable Transaction Manager')
                self.enabled = False

        log.debug('TransactionManager enabled: %s -> %s',
                  self.enabled, options)

    @property
    def injected(self):
        return self.enabled

    def __call__(self, controller, environ, context):
        if 'repoze.tm.active' in environ:  # pragma: no cover
            # Skip transaction manager if repoze.tm2 is enabled
            return self.next_handler(controller, environ, context)

        transaction_manager = self.manager
        total_attempts = self.attempts
        commit_veto = self.commit_veto

        attempts_left = total_attempts
        while attempts_left:
            attempts_left -= 1

            try:
                log.debug('Attempts Left %d (%d total)', attempts_left, total_attempts)
                transaction_manager.begin()

                t = transaction_manager.get()
                t.note(environ.get('PATH_INFO', ''))

                response = self.next_handler(controller, environ, context)
                if transaction_manager.isDoomed():
                    log.debug('Transaction doomed')
                    raise AbortTransaction(response)

                if commit_veto is not None:
                    veto = commit_veto(environ, response.status, response.headerlist)
                    if veto:
                        log.debug('Transaction vetoed')
                        raise AbortTransaction(response)

                transaction_manager.commit()
                log.debug('Transaction committed!')
                return response
            except AbortTransaction as e:
                transaction_manager.abort()
                return e.response
            except:
                exc_info = sys.exc_info()
                log.debug('Error while running request, aborting transaction')
                try:
                    can_retry = transaction_manager._retryable(*exc_info[:-1])
                    transaction_manager.abort()
                    if (attempts_left <= 0) or (not can_retry):
                        reraise(*exc_info)
                finally:
                    del exc_info
