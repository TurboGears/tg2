# -*- coding: utf-8 -*-
import copy
import logging

from ..utils import DependenciesList

log = logging.getLogger(__name__)


class Configurator(object):
    """Manage application configuration steps and blueprint.

    The configuration blueprint will be used as configuration foundation
    for every new application built from the Configurator, configuration
    blueprint is merged with deployment configuration loaded from
    config files before creating the application.

    Refer to each registered configuration step for configuration options
    available in the Configurator.

    .. versionadded:: 2.4
    """
    def __init__(self):
        self._initialized = False
        self._blueprint = {}
        self._coercion = {}
        self._steps = DependenciesList()

    def _initialize(self):
        if self._initialized:
            return

        for _, step in self._steps:
            step.on_bind(self)
        self._initialized = True

    def update_blueprint(self, config):
        """Add options from ``config`` to the configuration blueprint."""
        self._blueprint.update(config)

    def get_blueprint_value(self, name):
        try:
            return self._blueprint[name]
        except KeyError:
            raise KeyError("Blueprint does not provide a '{}' option".format(name))

    def register(self, config_step_type, after=None):
        """Registers a new configuration step to be performed by the Configurator"""
        if not issubclass(config_step_type, ConfigurationStep):
            raise ValueError('Configuration step must inherit ConfigurationStep')

        config_step = config_step_type()
        config_step._prepare_blueprint(self._blueprint)
        config_step._prepare_coercion(self._coercion)
        self._steps.add(config_step, key=config_step_type.id, after=after)

    def replace(self, stepid, new_config_step):
        """Replaces an existing configuration step with another one."""
        self._steps.replace(stepid, new_config_step)

    def get(self, stepid):
        return self._steps.get(stepid)

    def configure(self, global_conf=None, app_conf=None):
        self._initialize()

        conf = {}

        conf.update(copy.deepcopy(self._blueprint))
        conf.update(copy.deepcopy(global_conf))
        conf.update(app_conf)
        conf.update(dict(app_conf=app_conf, global_conf=global_conf))

        for _, step in self._steps:
            step._apply(BeforeConfigConfigurationAction, conf)

        log.debug("Initializing configuration, package: '%s'", conf.get('package_name'))
        return conf

    def setup(self, conf):
        for _, step in self._steps:
            step._apply(ConfigReadyConfigurationAction, conf)


class ConfigurationStep(object):
    """Represents a configuration step that as to be performed by :class:`.Configuration`.

    Each configurator step can perform multiple actions at different times,
    each action can be registered using :meth:`.ConfigurationStep.register`.

    .. versionadded:: 2.4
    """
    def __init__(self):
        if not hasattr(self, 'id'):
            raise ValueError('ConfigurationStep must provide an id class attribute '
                             'to uniquely identify it.')

        self._actions = {}
        for action in self.get_actions():
            self._register_action(action)

    def on_bind(self, configurator):
        """Called when ConfigurationStep is bound to a Configurator.

        This should be overridden to register global settings and
        entities like ApplicationWrappers and RenderingEngines into
        the configurator. It won't be called more than once per
        Configurator.
        """
        return

    def get_actions(self):
        """Can be overridden to provide a set of actions the step has the perform.

        Must return an iterable containing all the actions that must be
        performed by this configuration step::

            (BeforeConfigConfigurationAction(self.setup_config),
             ConfigReadyConfigurationAction(self.initialize_things),
             EnvironmentLoadedConfigurationAction(self.add_middleware))
        """
        return tuple()

    def get_defaults(self):
        """Can be overridden to provide default values for configuration blueprint.

        This is used when the configuration step is added to a Configurator to
        retrieve any default value for configuration options.

        Must return a dictionary in the form::

            {'option_name': 'value'}

        """
        return {}

    def get_coercion(self):
        """Can be overridden to provide coercion methods for options.

        Must return a dictionary in the form::

            {'option_name': cercion_function}
        """
        return {}

    def _register_action(self, action):
        self._actions.setdefault(action.__class__.__name__, []).append(action)

    def _prepare_blueprint(self, blueprint):
        defaults = self.get_defaults()
        for k,v in defaults.items():
            blueprint.setdefault(k, v)

    def _prepare_coercion(self, coercion):
        defaults = self.get_coercion()
        for k,v in defaults.items():
            coercion.setdefault(k, v)

    def _apply(self, action_type, conf, app=None):
        for action in self._actions.get(action_type.__name__, []):
            app = action(conf, app)
        return app

class _ConfigurationAction(object):
    """A :class:`ConfigurationStep` action.

    Represents what should be done during a part of a configuration step.

    .. versionadded:: 2.4
    """
    def __init__(self, perform=None):
        self.perform = perform

    def __call__(self, conf, app):
        return self.perform(conf, app)


class BeforeConfigConfigurationAction(_ConfigurationAction):
    pass


class ConfigReadyConfigurationAction(_ConfigurationAction):
    pass


class EnvironmentLoadedConfigurationAction(_ConfigurationAction):
    pass


class AppReadyConfigurationAction(_ConfigurationAction):
    pass


