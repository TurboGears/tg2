# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..base import ConfigurationComponent, ConfigReadyConfigurationAction, AppReadyConfigurationAction
from ...configuration.utils import TGConfigError
from ...support.middlewares import DBSessionRemoverMiddleware


class SQLAlchemyConfigurationComponent(ConfigurationComponent):
    """Support Relational Databases through SQLAlchemy.

    Configures SQLAlchemy connection to the database,
    the automatic session cleanup at the end of each request
    and support for master/slave databases.

    Support for transaction commit/rollback on request state
    is provided by :class:`.TransactionManagerConfigurationComponent`.

    The configured SQLAlchemy engine is made available as
    ``tg.app_globals.sa_engine``. While the configured SQLAlchemy
    session is made available as ``tg.config['SQLASession']``.

    Options:

        * ``use_sqlalchemy``: Enable SQLAlchemy in your application.
        * ``model``: Configure where models could be found, by default
                    they are expected in ``model`` Python module
                    within your application package.
        * ``sqlalchemy.*``: Options provided to SQLAlchemy connection
                           as expected by :func:`.engine_from_config`.
        * ``sqlalchemy.master.*`` Enable Master/Slave replication support
                                 and configure the master connection.
        * ``sqlalchemy.slaves.slavename.*``: Configure ``slavename`` slave in
                                            Master/Slave support and setup its
                                            connection. Multiple entries with
                                            different ``slavename`` values can
                                            be provided.

    """
    id = "sqlalchemy"

    def get_defaults(self):
        return {
            'use_sqlalchemy': False,
        }

    def get_actions(self):
        return (
            ConfigReadyConfigurationAction(self._setup_sqlalchemy),
            AppReadyConfigurationAction(self._add_middleware)
        )

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('SQLAlchemy Support only works on an ApplicationConfigurator')

    def _setup_sqlalchemy(self, conf, app):
        if not conf['use_sqlalchemy']:
            return
        self.setup_sqlalchemy(conf, app)

    def setup_sqlalchemy(self, conf, app):
        """Setup SQLAlchemy database engine"""
        engine = self.create_sqlalchemy_engine(conf)

        conf['tg.app_globals'].sa_engine = engine

        model = self._get_model(conf)
        sqla_session = model.init_model(engine)
        if sqla_session is not None:
            # If init_model returns a specific session, keep it around
            # as the SQLAlchemy Session.
            conf['SQLASession'] = sqla_session

        if 'DBSession' not in conf:
            # If the user hasn't specified a default session, assume
            # he/she uses the default DBSession in model
            conf['DBSession'] = model.DBSession

    def _add_middleware(self, conf, app):
        if not conf['use_sqlalchemy']:
            return app
        return self.add_middleware(conf, app)

    def add_middleware(self, conf, app):
        """Set up middleware that cleans up the sqlalchemy session.

        The default behavior of TG 2 is to clean up the session on every
        request.  Only override this method if you know what you are doing!

        """
        dbsession = conf.get('SQLASession')
        if dbsession is None:
            dbsession = conf['DBSession']
        return DBSessionRemoverMiddleware(dbsession, app)

    def _get_model(self, conf):
        try:
            package_models = conf['package'].model
        except AttributeError:
            package_models = None

        model = conf.get('model', package_models)
        if model is None:
            raise TGConfigError('SQLAlchemy enabled, but no models provided')

        return model

    @staticmethod
    def create_sqlalchemy_engine(conf):
        from sqlalchemy import engine_from_config
        balanced_master = conf.get('sqlalchemy.master.url')
        if not balanced_master:
            engine = engine_from_config(conf, 'sqlalchemy.')
        else:
            engine = engine_from_config(conf, 'sqlalchemy.master.')
            conf['balanced_engines'] = {'master': engine,
                                        'slaves': {},
                                        'all': {'master': engine}}

            all_engines = conf['balanced_engines']['all']
            slaves = conf['balanced_engines']['slaves']
            for entry in conf.keys():
                if entry.startswith('sqlalchemy.slaves.'):
                    slave_path = entry.split('.')
                    slave_name = slave_path[2]
                    if slave_name == 'master':
                        raise TGConfigError('A slave node cannot be named master')
                    slave_config = '.'.join(slave_path[:3])
                    all_engines[slave_name] = slaves[slave_name] = engine_from_config(conf, slave_config + '.')

            if not conf['balanced_engines']['slaves']:
                raise TGConfigError('When running in balanced mode your must specify at least a slave node')

        return engine
