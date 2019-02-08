"""Defines and initialises what is exposed as tg.config"""
from copy import deepcopy
from collections import MutableMapping as DictMixin
from tg.request_local import config as reqlocal_config
from tg.configuration.utils import get_partial_dict
from tg.util import Bunch


class _DispatchingConfigWrapper(DictMixin):
    """Wrapper for the Dispatching configuration.

    Simple wrapper for the DispatchingConfig object that provides attribute
    style access to the config dictionary.

    This class works by proxying all attribute and dictionary access to
    the underlying DispatchingConfig config object, which is an application local
    proxy that allows for multiple TG2 applications to live
    in the same process simultaneously, but to always get the right
    config data for the application that's requesting them.

    """

    def __init__(self, dict_to_wrap):
        """Initialize the object by passing in config to be wrapped"""
        self.__dict__['config_proxy'] = dict_to_wrap

    def __getitem__(self, key):
        return self.config_proxy.current_conf()[key]

    def __setitem__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __getattr__(self, key):
        """Our custom attribute getter.

        Tries to get the attribute off the wrapped object first,
        if that does not work, tries dictionary lookup, and finally
        tries to grab all keys that start with the attribute and
        return sub-dictionaries that can be looked up.

        """
        try:
            return self.config_proxy.__getattribute__(key)
        except AttributeError:
            try:
                return self.config_proxy.current_conf()[key]
            except KeyError:
                return get_partial_dict(key, self.config_proxy.current_conf(), Bunch)

    def __setattr__(self, key, value):
        self.config_proxy.current_conf()[key] = value

    def __delattr__(self, name):
        try:
            del self.config_proxy.current_conf()[name]
        except KeyError:
            raise AttributeError(name)

    def __delitem__(self, key):
        self.__delattr__(key)

    def __len__(self):
        return len(self.config_proxy.current_conf())

    def __iter__(self):
        return iter(self.config_proxy.current_conf())

    def __repr__(self):
        try:
            return repr(self.config_proxy.current_conf())
        except AttributeError:
            return '<TGConfig: missing>'

    def keys(self):
        return self.config_proxy.keys()


def _init_default_global_config():
    defaults = {
        'debug': False,
        'package': None,
        'tg.app_globals': None,
        'tg.strict_tmpl_context': True,
        'i18n.lang': None
    }

    # Push an empty config so all accesses to config at import time have something
    # to look at and modify. This config will be merged with the app's when it's
    # built in the paste.app_factory entry point.
    reqlocal_config.push_process_config(deepcopy(defaults))


# Create a config object that has attribute style lookup built in.
_init_default_global_config()
config = _DispatchingConfigWrapper(reqlocal_config)