import platform, sys

if platform.system() == 'Windows': # pragma: no cover
    WIN = True
else: # pragma: no cover
    WIN = False

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

if PY3:
    string_type = str
    unicode_text = str
    byte_string = bytes
    from urllib.parse import urlencode as url_encode
    from urllib.parse import quote as url_quote
    from urllib.parse import unquote as url_unquote

    def u_(s):
        return str(s)
else: # pragma: no cover
    string_type = basestring
    unicode_text = unicode
    byte_string = str
    from urllib import urlencode as url_encode
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote

    def u_(s):
        return unicode(s, 'utf-8')

def im_func(f):
    if PY3:
        return getattr(f, '__func__', None)
    else: # pragma: no cover
        return getattr(f, 'im_func', None)

def im_self(f):
    if PY3:
        return getattr(f, '__self__', None)
    else: # pragma: no cover
        return getattr(f, 'im_self', None)

def im_class(f):
    if PY3:
        self = im_self(f)
        if self is not None:
            return self.__class__
        else:
            return None
    else: # pragma: no cover
        return getattr(f, 'im_class', None)

def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})