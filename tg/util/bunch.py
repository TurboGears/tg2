from tg.configuration.utils import get_partial_dict


class Bunch(dict):
    """A dictionary that provides attribute-style access."""

    def __getitem__(self, key):
        return dict.__getitem__(self, key)

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return get_partial_dict(name, self, Bunch)

    __setattr__ = dict.__setitem__

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)
