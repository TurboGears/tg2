import warnings
from functools import update_wrapper


def no_warn(f, *args, **kwargs):
    """Decorator that suppresses warnings inside the decorated function"""
    def _f(*args, **kwargs):
        warnings.simplefilter("ignore")
        f(*args, **kwargs)
        warnings.resetwarnings()
    return update_wrapper(_f, f)


