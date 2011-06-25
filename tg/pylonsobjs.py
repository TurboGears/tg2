import warnings, sys
import pylons
import pylons.i18n


class DeprecatedWrapper(object):
    def __init__(self, obj, name):
        object.__setattr__(self, "__tg_pylons_obj", obj)
        object.__setattr__(self, "__tg_pylons_name", name)

    def _deprecation_warn(self, name=''):
        pylons_object_name = object.__getattribute__(self, '__tg_pylons_name')
        if not name.startswith('_'):
            warnings.warn("Directly accessing pylons.{0} objects is deprecated, please use the tg.{0}".format(pylons_object_name), DeprecationWarning, stacklevel=3)

    def __getattribute__(self, name):
        if name == '_deprecation_warn':
            return object.__getattribute__(self, '_deprecation_warn')
        self._deprecation_warn(name)
        return getattr(object.__getattribute__(self, "__tg_pylons_obj"), name)
    def __delattr__(self, name):
        self._deprecation_warn(name)
        delattr(object.__getattribute__(self, "__tg_pylons_obj"), name)
    def __setattr__(self, name, value):
        self._deprecation_warn(name)
        setattr(object.__getattribute__(self, "__tg_pylons_obj"), name, value)
   
    def __getitem__(self, name):
        self._deprecation_warn(name)
        return object.__getitem__(object.__getattribute__(self, "__tg_pylons_obj"), name)
    def __delitem__(self, name):
        self._deprecation_warn(name)
        object.__delitem__(object.__getattribute__(self, "__tg_pylons_obj"), name)
    def __setitem__(self, name, value):
        self._deprecation_warn(name)
        object.__setitem__(object.__getattribute__(self, "__tg_pylons_obj"), name, value)
 
    def __nonzero__(self):
        self._deprecation_warn()
        return bool(object.__getattribute__(self, "__tg_pylons_obj"))
    def __str__(self):
        self._deprecation_warn()
        return str(object.__getattribute__(self, "__tg_pylons_obj"))
    def __repr__(self):
        self._deprecation_warn()
        return repr(object.__getattribute__(self, "__tg_pylons_obj"))

from pylons import templating, configuration, config, i18n

__all__ = ['app_globals', 'request', 'response', 'session', 
           'tmpl_context', 'cache']

#Monkeypatch pylons object to provide a deprecation warning
current_module = sys.modules[__name__]
for pylons_obj_name in __all__:
    pylons_obj = getattr(pylons, pylons_obj_name)
    setattr(current_module, pylons_obj_name, pylons_obj)
    setattr(pylons, pylons_obj_name, DeprecatedWrapper(pylons_obj, pylons_obj_name))
    
