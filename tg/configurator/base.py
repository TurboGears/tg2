# -*- coding: utf-8 -*-
import logging
import weakref

from ..configuration.utils import DependenciesList, coerce_options, DictionaryView, copyoption

log = logging.getLogger(__name__)


class Configurator(object):
    """Manages a configuration process with multiple components and steps.

    Multiple registered components will be configured by applying
    the options provided during configuration on top of a bluepint
    (a set of default options).

    The result will be a configuration dictionary and whatever side effect
    each component triggered when being configured.

    This doesn't really know anything about that it is configuring
    and is not TurboGears specific. An ``ApplicationConfigurator``
    is provided which is a specialised ``Configurator`` for configuring
    TurboGears applications.

    .. versionadded:: 2.4
    """
    def __init__(self):
        self._initialized = False
        self._blueprint = {}
        self._coercion = {}
        self._components = DependenciesList()

    def _initialize(self):
        if self._initialized:
            return

        for _, component in self._components:
            component.on_bind(self)
        self._initialized = True

    def update_blueprint(self, config):
        """Add options from ``config`` to the configuration blueprint."""
        self._blueprint.update(config)

    def get_blueprint_value(self, name):
        """Get an option registered into the configuration blueprint."""
        try:
            return self._blueprint[name]
        except KeyError:
            raise KeyError("Configuration Blueprint does not provide a '{0}' option".format(name))

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

    def register(self, component_type, after=None):
        """Registers a new configuration component to be performed by the Configurator"""
        if not issubclass(component_type, ConfigurationComponent):
            raise ValueError('Configuration component must inherit ConfigurationComponent')

        component = component_type()
        component._prepare_blueprint(self._blueprint)
        component._prepare_coercion(self._coercion)
        self._components.add(component, key=component_type.id, after=after)

    def replace(self, component_id, new_component_type):
        """Replaces an existing configuration component with another one.

        Any default value set in the blueprint by the previous component
        won't be discarded and won't be replaced. So if you tuned the configuration
        of the previous component, the new one will preserve it.

        Also the id at which the component is registered won't be the one
        of the new component, but will be the one of the old component.

        In theory you should only replace components with components that
        provide same id and same default options.

        Note that replacing a component will only influence the applications
        created after it was replaced.
        """
        if not issubclass(new_component_type, ConfigurationComponent):
            raise ValueError('Configuration component must inherit ConfigurationComponent')

        component = new_component_type()
        component._prepare_blueprint(self._blueprint)
        component._prepare_coercion(self._coercion)
        self._components.replace(component_id, component)

    def get_component(self, component_id):
        """Retrieve a registered configuration component."""
        return self._components.get(component_id)

    def configure(self, global_conf=None, app_conf=None):
        """Prepare a configuration using the configurator.

        Once it's ready the configuration is returned.
        """
        self._initialize()

        conf = {}

        conf.update(copyoption(self._blueprint))
        conf.update(copyoption(global_conf))
        conf.update(app_conf)

        # Let track of the configurator that generated the configuration
        # into the configuration itself.
        conf['tg.configurator'] = weakref.ref(self)

        # Convert the loaded options according to the coercion functions
        # registered by each configuration component.
        conf.update(coerce_options(conf, self._coercion))

        for _, component in self._components:
            component._apply(BeforeConfigConfigurationAction, conf)

        log.debug("Initializing configuration, package: '%s'", conf.get('package_name'))
        return conf

    def setup(self, conf):
        """Given a configuration setup the environment.

        Applies ``ConfigReadyConfigurationAction`` configuration actions
        from the registered components.

        This usually involves all the configuration steps that already
        need to have all configuration options available before they can proceed.
        """
        for _, component in self._components:
            component._apply(ConfigReadyConfigurationAction, conf)


class ConfigurationComponent(object):
    """Represents a configuration component that will collaborate in configuring an application.

    Each component once registered in a :class:`.Configurator` can perform multiple
    actions at different times, each action can be registered by
    returing them through :meth:`.get_actions`.

    .. versionadded:: 2.4
    """
    def __init__(self):
        if not hasattr(self, 'id'):
            raise ValueError('ConfigurationComponent must provide an id class attribute '
                             'to uniquely identify the component.')

        self._actions = {}
        for action in self.get_actions():
            self._register_action(action)

    def on_bind(self, configurator):
        """Called when component is bound to a Configurator.

        This should be overridden to register global settings and
        entities like ApplicationWrappers and RenderingEngines into
        the configurator. It won't be called more than once per
        Configurator.
        """
        return

    def get_actions(self):
        """Can be overridden to provide a set of actions the component has the perform.

        Must return an iterable containing all the actions that must be
        performed by this configuration component at any given time::

            (BeforeConfigConfigurationAction(self.setup_config),
             ConfigReadyConfigurationAction(self.initialize_things),
             EnvironmentLoadedConfigurationAction(self.add_middleware))
        """
        return tuple()

    def get_defaults(self):
        """Can be overridden to provide default values for configuration blueprint.

        This is used when the configuration component is added to a Configurator to
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
    """An action done by a :class:`,ConfigurationComponent` during configuration process.

    Represents what should be done during part of configuration
    process by a :class:`ConfigurationComponent`.
    The :class:`.Configurator` will fire the actions at specific
    times based on the action type.

    .. versionadded:: 2.4
    """
    def __init__(self, perform=None):
        self.perform = perform

    def __repr__(self):
        return '<%s: %r>' % (self.__class__.__name__, self.perform)

    def __call__(self, conf, app):
        return self.perform(conf, app)


class BeforeConfigConfigurationAction(_ConfigurationAction):
    """An action to be executed before the app configuration is initialised."""
    pass


class ConfigReadyConfigurationAction(_ConfigurationAction):
    """An action to be executed once the configuration is loaded and ready."""
    pass


class EnvironmentLoadedConfigurationAction(_ConfigurationAction):
    """An action to be executed once the environment needed to create the app is ready."""
    pass


class AppReadyConfigurationAction(_ConfigurationAction):
    """An action to be executed once the application has been created.

    It's typically the best time where to wrap WSGI middlewares
    around the application.
    """
    pass
