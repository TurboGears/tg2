import inspect
from collections import deque

import itertools

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
        raise AttributeError(prefix)


class GlobalConfigurable(object):
    """Defines a configurable TurboGears object with a global default instance.

    GlobalConfigurable are objects which the user can create multiple instances to use
    in its own application or third party module, but for which TurboGears provides
    a default instance.

    Common examples are ``tg.flash`` and the default JSON encoder for which
    TurboGears provides default instances of ``.TGFlash`` and ``.JSONEncoder`` classes
    but users can create their own.

    While user created versions are configured calling the :meth:`.GlobalConfigurable.configure`
    method, global versions are configured by :class:`.ApplicationConfigurator` which
    configures them when ``config_ready`` milestone is reached.

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
        """Creates a global instance whose configuration is linked to ``tg.config``."""
        if cls.CONFIG_NAMESPACE is None:
            raise TGConfigError('Must specify a CONFIG_NAMESPACE attribute in class for the'
                                'namespace used by all configuration options.')

        obj = cls()
        config_ready.register(obj._load_config, persist_on_reset=True)
        return obj

    def _load_config(self):
        from tg.configuration import config
        self.configure(**coerce_config(config, self.CONFIG_NAMESPACE,  self.CONFIG_OPTIONS))


class DependenciesList(object):
    """Manages a list of entries which might depend one from the other.

    This powers everything that needs to keep track of a list of entries that
    might have dependencies one to the other and keeps them linearised according
    to the dependencies. This powers the resolution of ConfigurationComponenets,
    ApplicationsWrappers and so on...

    .. note:: This is highly inefficient as it is only meant to run at configuration time,
              a new implementation will probably be provided based on heapq in the future.
    """
    #: Those are the heads of the dependencies tree
    #:  - ``False`` means before everything else
    #:  - ``None`` means in the middle.
    #:  - ``True`` means after everything else.
    DEPENDENCY_HEADS = (False, None, True)

    def __init__(self, *entries):
        self._dependencies = {}
        self._ordered_elements = []
        self._inserted_keys = []

        for entry in entries:
            self.add(entry)

    def add(self, entry, key=None, after=None):
        """Adds an entry to the dependencies list.

        :param entry: Entry that must be added to the list.
        :param str|type|None key: An identifier of the object being inserted.
                                  This is used by later insertions as ``after`` argument
                                  to specify after which object the new one should be inserted.
        :param str|type|None|False|True after: After which element this one should be inserted.
                                               This is the ``key`` of a previously inserted item.
                                               In case no item with ``key`` has been inserted, the
                                               entry will be inserted in normal order of insertion.
                                               Also accepts one of
                                               :attr:`.DependenciesList.DEPENDENCY_HEADS` as key
                                               to add entries at begin or end of the list.
        """
        if key is None:
            if inspect.isclass(entry):
                key = entry.__name__
            else:
                # Inserting an object without a key would lead to unexpected ordering.
                # we cannot use the object class as the key would not be unique across
                # different instances.
                raise ValueError('Inserting instances without a key is not allowed')

        if after not in self.DEPENDENCY_HEADS and not isinstance(after, str):
            if inspect.isclass(after):
                after = after.__name__
            else:
                raise ValueError('after parameter must be a string, a class or a special value')

        if key in self._inserted_keys:
            raise KeyError('Already existing entry for this key')

        self._inserted_keys.append(key)
        self._dependencies.setdefault(after, []).append((key, entry))
        self._resolve_ordering()

    def __repr__(self):
        return '<DependenciesList %s>' % [x[0] for x in self._ordered_elements]

    def __iter__(self):
        return iter(self._ordered_elements)

    def values(self):
        """Returns all the inserted values without their key as a generator"""
        return (x[1]for x in self._ordered_elements)

    def replace(self, key, newvalue):
        """Replaces entry associated to key with a new one.

        :param newvalue: Entry that must replace the previous value.
        :param str|type key: An identifier of the object being inserted.
        """
        if not isinstance(key, str):
            if inspect.isclass(key):
                key = key.__name__
            else:
                raise ValueError('key parameter must be a string or a class')

        for entries in self._dependencies.values():
            for idx, value in enumerate(entries):
                entry_key, entry_value = value
                if entry_key == key:
                    entries[idx] = (entry_key, newvalue)

        self._resolve_ordering()

    def get(self, key):
        if not isinstance(key, str):
            if inspect.isclass(key):
                key = key.__name__
            else:
                raise ValueError('key parameter must be a string or a class')

        for entries in self._dependencies.values():
            for idx, value in enumerate(entries):
                entry_key, entry_value = value
                if entry_key == key:
                    return entry_value

        return None

    def _resolve_ordering(self):
        ordered_elements = []

        existing_dependencies = set(self._inserted_keys) | set(self.DEPENDENCY_HEADS)
        dependencies_without_heads = set(self._dependencies.keys()) - set(self.DEPENDENCY_HEADS)

        # All entries that depend on a missing entry are converted
        # to depend from None so they end up being in the middle.
        dependencies = {}
        for dependency in itertools.chain(self.DEPENDENCY_HEADS, dependencies_without_heads):
            entries = self._dependencies.get(dependency, [])
            if dependency not in existing_dependencies:
                dependency = None
            dependencies.setdefault(dependency, []).extend(entries)

        # Resolve the dependencies and generate the ordered elements.
        visit_queue = deque((head, head) for head in self.DEPENDENCY_HEADS)
        while visit_queue:
            current_key, current_obj = visit_queue.popleft()
            if current_key not in self.DEPENDENCY_HEADS:
                ordered_elements.append((current_key, current_obj))

            element_dependencies = dependencies.pop(current_key, [])
            visit_queue.extendleft(reversed(element_dependencies))

        self._ordered_elements = ordered_elements


class DictionaryView(object):
    """Provides a view on a slice of a dictionary.

    This allows to expose all keys in a dictionary
    that start with a common prefix as a subdictionary.

    For example you might expose all keys starting with
    sqlalchemy.* as a standalone dictionary, all changes
    to the view will reflect into the dictionary updating
    the original keys.
    """
    __slots__ = ('_d', '_keypath')

    def __init__(self, d, keypath):
        if keypath and keypath[-1] != '.':
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