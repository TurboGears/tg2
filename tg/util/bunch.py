def get_partial_dict(
    prefix, dictionary, container_type=dict, ignore_missing=False, pop_keys=False
):
    """Given a dictionary and a prefix, return a Bunch, with just items
    that start with prefix

    The returned dictionary will have 'prefix.' stripped so::

        get_partial_dict('prefix', {'prefix.xyz':1, 'prefix.zyx':2, 'xy':3})

    would return::

        {'xyz':1,'zyx':2}
    """

    match = prefix + "."
    n = len(match)

    new_dict = container_type(
        ((key[n:], dictionary[key]) for key in dictionary if key.startswith(match))
    )

    if pop_keys:
        for key in list(dictionary.keys()):
            if key.startswith(match):
                dictionary.pop(key, None)

    if new_dict:
        return new_dict
    else:
        if ignore_missing:
            return {}
        raise AttributeError(prefix)


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
