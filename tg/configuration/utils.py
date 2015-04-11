from .milestones import config_ready


class TGConfigError(Exception):pass


def coerce_options(options, converters):
    """Convert some configuration options to expected types.

    To replace given options with the converted values
    in a dictionary you might do::

        conf.update(coerce_options(conf, {
            'debug': asbool,
            'serve_static': asbool,
            'auto_reload_templates': asbool
        }))
    """
    converted_options = {}
    for option, converter in converters.items():
        if option in options:
            converted_options[option] = converter(options[option])
    return converted_options


def coerce_config(configuration, prefix, converters):
    """Extracts a set of options with a common prefix and converts them.

    To extract all options starting with ``trace_errors.`` from
    the ``conf`` dictionary and conver them::

        trace_errors_config = coerce_config(conf, 'trace_errors.', {
            'smtp_use_tls': asbool,
            'dump_request_size': asint,
            'dump_request': asbool,
            'dump_local_frames': asbool,
            'dump_local_frames_count': asint
        })
    """

    options = dict((key[len(prefix):], configuration[key])
                    for key in configuration if key.startswith(prefix))
    options.update(coerce_options(options, converters))
    return options

def get_partial_dict(prefix, dictionary, container_type=dict):
    """Given a dictionary and a prefix, return a Bunch, with just items
    that start with prefix

    The returned dictionary will have 'prefix.' stripped so::

        get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3})

    would return::

        {'xyz':1,'zyx':2}
    """

    match = prefix + "."
    n = len(match)

    new_dict = container_type(((key[n:], dictionary[key])
                                for key in dictionary
                                if key.startswith(match)))
    if new_dict:
        return new_dict
    else:
        raise AttributeError


class GlobalConfigurable(object):
    """Defines a configurable TurboGears object with a global default instance.

    GlobalConfigurable are objects which the user can create multiple instances to use
    in its own application or third party module, but for which TurboGears provides
    a default instance.

    Common examples are ``tg.flash`` and the default JSON encoder for which
    TurboGears provides default instances of ``.TGFlash`` and ``.JSONEncoder`` classes
    but users can create their own.

    While user created versions are configured calling the :meth:`.GlobalConfigurable.configure`
    method, global versions are configured by :class:`.AppConfig` which configures them when
    ``config_ready`` milestone is reached.

    """
    CONFIG_NAMESPACE = None
    CONFIG_OPTIONS = {}

    def configure(self, **options):
        """Expected to be implemented by each object to proceed with actualy configuration.

        Configure method will receive all the options whose name starts with ``CONFIG_NAMESPACE``
        (example ``json.isodates`` has ``json.`` namespace).

        If ``CONFIG_OPTIONS`` is specified options values will be converted with
        :func:`coerce_config` passing ``CONFIG_OPTIONS`` as the ``converters`` dictionary.

        """
        raise NotImplementedError('GlobalConfigurable objects must implement a configure method')

    @classmethod
    def create_global(cls):
        """Creates a global instance which configuration will be bound to :class:`.AppConfig`."""
        if cls.CONFIG_NAMESPACE is None:
            raise TGConfigError('Must specify a CONFIG_NAMESPACE attribute in class for the'
                                'namespace used by all configuration options.')

        obj = cls()
        config_ready.register(obj._load_config, persist_on_reset=True)
        return obj

    def _load_config(self):
        from tg.configuration import config
        self.configure(**coerce_config(config, self.CONFIG_NAMESPACE,  self.CONFIG_OPTIONS))
