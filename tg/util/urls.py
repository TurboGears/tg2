import urllib.parse


def _smart_str(s):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    This function was borrowed from Django.

    """
    if isinstance(s, bytes):
        return s
    elif isinstance(s, str):
        return s.encode("utf-8", "strict")
    else:
        try:
            return str(s).encode("ascii", "strict")
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return " ".join(
                    [_smart_str(arg).decode("utf-8") for arg in s.args]
                ).encode("utf-8", "strict")
            return str(s).encode("utf-8", "strict")


def _generate_smart_str(params):
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                yield _smart_str(key), _smart_str(item)
        else:
            yield _smart_str(key), _smart_str(value)


def _urlencode(params):
    """
    A version of Python's urllib.urlencode() function that can operate on
    unicode strings. The parameters are first case to UTF-8 encoded strings and
    then encoded as per normal.
    """
    return urllib.parse.urlencode([i for i in _generate_smart_str(params)])


def build_url(environ, base_url="/", params=None):
    """Build a URL based on the given WSGI environ, a base URL and its parameters."""
    if base_url.startswith("/"):
        base_url = environ["SCRIPT_NAME"] + base_url

    if params:
        return "?".join((base_url, _urlencode(params)))

    return base_url
