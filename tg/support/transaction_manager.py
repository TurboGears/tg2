from tg._compat import reraise
from tg.request_local import Request
import sys
import transaction

import logging
log = logging.getLogger('tg.transaction_manager')


class AbortTransaction(Exception):
    def __init__(self, response_data):
        self.response_data = response_data


class TGTransactionManager(object):
    def __init__(self, app, config):
        self.app = app
        self.config = config

        self.attempts = config.get('tm.attempts', 1)
        self.commit_veto = config.get('tm.commit_veto', None)

    def __call__(self, environ, start_response):
        if 'repoze.tm.active' in environ: #pragma: no cover
            #Skip transaction manager if repoze.tm2 is enabled
            return self.app(environ, start_response)

        transaction_manager = transaction.manager
        total_attempts = self.attempts
        commit_veto = self.commit_veto
        started_response = {}

        def _start_response(status, headers, exc_info=None):
            started_response.update(status=status, headers=headers)
            return start_response(status, headers, exc_info)

        attempts_left = total_attempts
        while attempts_left:
            attempts_left -= 1

            try:
                log.debug('Attempts Left %d (%d total)', attempts_left, total_attempts)
                transaction_manager.begin()

                if total_attempts > 1:
                    Request(environ).make_body_seekable()

                t = transaction_manager.get()
                t.note(environ.get('PATH_INFO', ''))

                response_data = self.app(environ, _start_response)
                if transaction_manager.isDoomed():
                    log.debug('Transaction doomed')
                    raise AbortTransaction(response_data)

                if commit_veto is not None:
                    veto = commit_veto(environ, started_response['status'], started_response['headers'])
                    if veto:
                        log.debug('Transaction vetoed')
                        raise AbortTransaction(response_data)

                transaction_manager.commit()
                log.debug('Transaction committed!')
                return response_data
            except AbortTransaction as e:
                transaction_manager.abort()
                return e.response_data
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
