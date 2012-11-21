
class TurboGearsObjectProxy(object):
    """
    Foundation for the TurboGears request locals
    and StackedObjectProxy.

    Mostly inspired by paste.registry.StackedObjectProxy
    """
    def __dir__(self):
        dir_list = dir(self.__class__) + list(self.__dict__.keys())
        try:
            dir_list.extend(dir(self._current_obj()))
        except TypeError:
            pass
        dir_list.sort()
        return dir_list

    def __getattr__(self, attr):
        return getattr(self._current_obj(), attr)

    def __setattr__(self, attr, value):
        setattr(self._current_obj(), attr, value)

    def __delattr__(self, name):
        delattr(self._current_obj(), name)

    def __getitem__(self, key):
        return self._current_obj()[key]

    def __setitem__(self, key, value):
        self._current_obj()[key] = value

    def __delitem__(self, key):
        del self._current_obj()[key]

    def __call__(self, *args, **kw):
        return self._current_obj()(*args, **kw)

    def __repr__(self):
        try:
            return repr(self._current_obj())
        except (TypeError, AttributeError):
            return '<%s.%s object at 0x%x>' % (self.__class__.__module__,
                                               self.__class__.__name__,
                                               id(self))

    def __iter__(self):
        return iter(self._current_obj())

    def __len__(self):
        return len(self._current_obj())

    def __contains__(self, key):
        return key in self._current_obj()

    def __nonzero__(self):
        return bool(self._current_obj())