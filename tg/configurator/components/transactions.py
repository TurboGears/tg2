# -*- coding: utf-8 -*-
from __future__ import absolute_import

from tg.support.converters import asbool
from ..base import ConfigurationComponent
from ...configuration.utils import TGConfigError


class TransactionManagerConfigurationComponent(ConfigurationComponent):
    """Support for transaction manager.

    The transaction manager will automatically handle transactions
    bound to it according to the request state.

    Whenever a request succeeds the transaction manger will
    commit all transactions, while in case of a failure it will
    rollback the transactions.

    Refer to :class:`.TransactionApplicationWrapper` for list of
    supported options.
    """
    id = "transaction_manager"

    def get_defaults(self):
        return {
            'tm.enabled': True
        }

    def get_coercion(self):
        return {
            'tm.enabled': asbool
        }

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('Transactions Support only works on an ApplicationConfigurator')

        from ...appwrappers.transaction_manager import TransactionApplicationWrapper
        configurator.register_application_wrapper(TransactionApplicationWrapper, after=True)
