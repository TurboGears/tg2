from ..request_local import request as tg_request
from ..util.urls import build_url


def url(base_url="/", params=None, qualified=False, scheme=None):
    """Generate an absolute URL that's specific to this application.

    The URL function takes a string (base_url) and, appends the
    SCRIPT_NAME and adds parameters for all of the
    parameters passed into the params dict.

    ``scheme`` can be passed in case of a ``qualified`` url to
    create an url with the given scheme.

    """
    if not isinstance(base_url, str) and hasattr(base_url, "__iter__"):
        base_url = "/".join(base_url)

    req = tg_request._current_obj()
    base_url = build_url(req.environ, base_url, params)
    if qualified:
        base_url = req.host_url + base_url
        if scheme is not None:
            base_url = scheme + base_url[len(req.scheme) :]

    return base_url


class LazyUrl(object):
    """
    Wraps tg.url in an object that enforces evaluation of the url
    only when you try to display it as a string.
    """

    def __init__(self, base_url, params=None, **kwargs):
        self.base_url = base_url
        self.params = params
        self.kwargs = kwargs
        self._decoded = None

    @property
    def _id(self):
        if self._decoded is None:
            self._decoded = url(self.base_url, params=self.params, **self.kwargs)
        return self._decoded

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return self._id

    def __html__(self):
        return str(self)

    def __str__(self):
        return str(self._id)

    def encode(self, *args, **kw):
        return self._id.encode(*args, **kw)

    def __add__(self, other):
        return self._id + other

    def __radd__(self, other):
        return other + self._id

    def startswith(self, *args, **kw):
        return self._id.startswith(*args, **kw)

    def format(self, *args, **kwargs):
        return self._id.format(*args, **kwargs)

    def __json__(self):
        return str(self)


def lurl(base_url=None, params=None, **kwargs):
    """
    Like tg.url but is lazily evaluated.

    This is useful when creating global variables as no
    request is in place.

    As without a request it wouldn't be possible
    to correctly calculate the url using the SCRIPT_NAME
    this demands the url resolution to when it is
    displayed for the first time.
    """
    return LazyUrl(base_url, params, **kwargs)
