# -*- coding: utf-8 -*-
from __future__ import absolute_import
from ..base import (ConfigurationComponent, BeforeConfigConfigurationAction, ConfigReadyConfigurationAction,
                    AppReadyConfigurationAction)
from ...configuration.utils import get_partial_dict, TGConfigError
from ...support.converters import asbool, asint


class MingConfigurationComponent(ConfigurationComponent):
    """Support MongoDB through the Ming Object Document Mapper.

    Configures the ming connection to MongoDB,
    the automatic session cleanup at the end of each request
    and support for the UnitOfWork flushing/discard based
    on request success or failures.

    The configured Ming session is made available as
    ``tg.config['MingSession']``.

    Options:

        * ``ming.enabled``: Enable Ming in your application
        * ``ming.url``: MongoDB url to connect to.
        * ``ming.db``: Database to use. Can also be specified in ``ming.url``.
        * ``ming.autoflush``: Automatically flush the unit of work as the end
                              of each request, unless there was a failure.
        * ``ming.connection.*``: Options provided to the ming engine to configure
                                 the datastore and the ``MongoClient``. Refer to
                                 :class:`.MongoClient` for available options.

    See :class:`.MingApplicationWrapper` for additional
    configuration options.
    """
    id = "ming"

    def get_defaults(self):
        return {
            'use_ming': False
        }

    def get_coercion(self):
        def mongo_read_pref(value):
            from pymongo.read_preferences import ReadPreference
            return getattr(ReadPreference, value)

        return {
            'use_ming': asbool,  # backward compatibility for ming.enabled
            'ming.enabled': asbool,
            'ming.autoflush': asbool,
            'ming.connection.max_pool_size': asint,
            'ming.connection.network_timeout': asint,
            'ming.connection.tz_aware': asbool,
            'ming.connection.safe': asbool,
            'ming.connection.journal': asbool,
            'ming.connection.wtimeout': asint,
            'ming.connection.fsync': asbool,
            'ming.connection.ssl': asbool,
            'ming.connection.read_preference': mongo_read_pref,
            'ming.connection.auto_ensure_indexes': asbool
        }

    def get_actions(self):
        return (
            BeforeConfigConfigurationAction(self.configure),
            ConfigReadyConfigurationAction(self.setup),
            AppReadyConfigurationAction(self.add_middleware),
        )

    def on_bind(self, configurator):
        from ..application import ApplicationConfigurator
        if not isinstance(configurator, ApplicationConfigurator):
            raise TGConfigError('Ming Support only works on an ApplicationConfigurator')

        from ...appwrappers.mingflush import MingApplicationWrapper
        configurator.register_application_wrapper(MingApplicationWrapper, after=True)

    def configure(self, conf, app):
        try:
            autoflush_enabled = conf['ming.autoflush']
        except KeyError:
            autoflush_enabled = True

        conf.setdefault('ming.enabled', conf.get('use_ming', False))
        conf['ming.autoflush'] = conf['ming.enabled'] and autoflush_enabled

    def setup(self, conf, app):
        """Setup MongoDB database engine using Ming"""
        if not conf['ming.enabled']:
            return

        datastore = self.create_ming_datastore(conf)
        conf['tg.app_globals'].ming_datastore = datastore

        model = self._get_models(conf)
        ming_session = model.init_model(datastore)
        if ming_session is not None:
            # If init_model returns a specific session, keep it around
            # as the MongoDB Session.
            conf['MingSession'] = ming_session

        if 'DBSession' not in conf:
            # If the user hasn't specified a default session, assume
            # he/she uses the default DBSession in model
            conf['DBSession'] = model.DBSession

    def add_middleware(self, conf, app):
        """Set up the ming middleware for the unit of work"""
        if not conf['ming.enabled']:
            return app

        from tg.support.middlewares import MingSessionRemoverMiddleware
        from ming.odm import ThreadLocalODMSession
        return MingSessionRemoverMiddleware(ThreadLocalODMSession, app)

    def _get_models(self, conf):
        try:
            package_models = conf['package'].model
        except AttributeError:
            package_models = None

        model = conf.get('model', package_models)
        if model is None:
            raise TGConfigError('Ming enabled, but no models provided')

        return model

    @staticmethod
    def create_ming_datastore(conf):
        from ming import create_datastore
        url = conf['ming.url']
        database = conf.get('ming.db', '')
        try:
            connection_options = get_partial_dict('ming.connection', conf)
        except AttributeError:
            connection_options = {}
        if database and url[-1] != '/':
            url += '/'
        ming_url = url + database
        return create_datastore(ming_url, **connection_options)