class TGConfigError(Exception):pass


def coerce_config(configuration, prefix, converters):
    """Convert configuration values to expected types."""

    options = dict((key[len(prefix):], configuration[key])
                    for key in configuration if key.startswith(prefix))

    for option, converter in converters.items():
        if option in options:
            options[option] = converter(options[option])

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