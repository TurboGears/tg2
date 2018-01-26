# -*- coding: utf-8 -*-
import logging

from ..utils import DependenciesList, coerce_options
from ..hooks import hooks

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
        """Get an option registered into the configuration blueprint."""
        try:
            return self._blueprint[name]
        except KeyError:
            raise KeyError("Configuration Blueprint does not provide a '{}' option".format(name))

    def get_blueprint_view(self, key):
        """A view is a subset of the blueprint options.

        If the blueprint contains multiple values that share
        a common prefix it is possible to get a view that
        contains them all. A view acts like a dictionary
        where it is possible to get or set the values.

        Given a blueprint that contains ``section.option1`` and
        ``section.option2`` it is possible to ask for the view
        of ``section`` and get back a dictionary like object
        that contains ``option1`` and ``option2``.
        """
        if key.endswith('.'):
            raise ValueError('A Blueprint key cannot end with a .')
        return DictionaryView(self._blueprint, key)

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
        """Retrieve a registered configuration step."""
        return self._steps.get(stepid)

    def configure(self, global_conf=None, app_conf=None):
        self._initialize()

        conf = {}

        conf.update(copyoption(self._blueprint))
        conf.update(copyoption(global_conf))
        conf.update(app_conf)

        # Convert the loaded options according to the coercion functions
        # registered by each configuration step.
        conf.update(coerce_options(conf, self._coercion))

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

            {'option_name': coerce_function}
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
            log.debug('%s applying %s', self.__class__.__name__, action)
            app = action(conf, app)
        return app


class _ConfigurationAction(object):
    """A :class:`ConfigurationStep` action.

    Represents what should be done during a part of a configuration step.

    .. versionadded:: 2.4
    """
    def __init__(self, perform=None):
        self.perform = perform

    def __repr__(self):
        return '<%s: %r>' % (self.__class__.__name__, self.perform)

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


# TODO: Move into utils
class DictionaryView(object):
    __slots__ = ('_d', '_keypath')

    def __init__(self, d, keypath):
        if keypath[-1] != '.':
            keypath = keypath + '.'
        self._d = d
        self._keypath = keypath

    def __getitem__(self, item):
        key = self._keypath + item
        return self._d[key]

    def __setitem__(self, key, value):
        key = self._keypath + key
        self._d[key] = value

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            key = self._keypath + item
            raise AttributeError(key)

    def __setattr__(self, key, value):
        if key not in self.__slots__:
            self.__setitem__(key, value)
        else:
            object.__setattr__(self, key, value)

    def update(self, d, **d2):
        if hasattr(d, 'keys'):
            for key in d.keys():
                self[key] = d[key]
        else:
            for key, value in d:
                self[key] = value

        for key in d2:
            self[key] = d2[key]


# TODO: Move into utils
def copyoption(v):
    """Copies a dictionary and all its nested dictionaries and lists.

    Much like copy.deepcopy it provides a deep copy of a dictionary
    but instead of trying to copy everything it will only make a copy
    of dictionaries, lists, tuples and sets. All the containers typically
    used in configuration blueprints. All the other objects will be
    preserved by reference.
    """
    if isinstance(v, dict):
        return v.__class__((k, copyoption(v[k])) for k in v)
    elif isinstance(v, (list, set, tuple)):
        return v.__class__(copyoption(e) for e in v)
    else:
        # Preserve anything else as is.
        return v