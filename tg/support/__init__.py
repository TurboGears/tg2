"""Support modules for TG features.

Support modules implement components that are used by TurboGears
to provide the user level API. The support modules will usually
rely on TurboGears specific objects and modules to provide their
functionality.
"""


class NoDefault(object):
    pass


class EmptyContext(object):
    """
    Noop Python Context, does nothing but can be used
    in a with statement to provide a default context.
    """

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
