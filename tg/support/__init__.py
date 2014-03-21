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