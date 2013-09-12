class TGConfigError(Exception):pass


def coerce_config(configuration, prefix, converters):
    """Convert configuration values to expected types."""

    options = dict((key[len(prefix):], configuration[key])
                    for key in configuration if key.startswith(prefix))

    for option, converter in converters.items():
        if option in options:
            options[option] = converter(options[option])

    return options
