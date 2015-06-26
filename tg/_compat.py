import platform, sys

if platform.system() == 'Windows': # pragma: no cover
    WIN = True
else: # pragma: no cover
    WIN = False

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3
PY2 = sys.version_info[0] == 2


if PY3: # pragma: no cover
    string_type = str
    unicode_text = str
    byte_string = bytes
    from urllib.parse import urlencode as url_encode
    from urllib.parse import quote as url_quote
    from urllib.parse import unquote as url_unquote
    from urllib.request import url2pathname

    def u_(s):
        return str(s)

    def bytes_(s):
        return str(s).encode('ascii', 'strict')
else:
    string_type = basestring
    unicode_text = unicode
    byte_string = str
    from urllib import urlencode as url_encode
    from urllib import quote as url_quote
    from urllib import unquote as url_unquote
    from urllib import url2pathname

    def u_(s):
        return unicode(s, 'utf-8')

    def bytes_(s):
        return str(s)

def im_func(f):
    if PY3: # pragma: no cover
        return getattr(f, '__func__', None)
    else:
        return getattr(f, 'im_func', None)

def default_im_func(f):
    if PY3: # pragma: no cover
        return getattr(f, '__func__', f)
    else:
        return getattr(f, 'im_func', f)

def im_self(f):
    if PY3: # pragma: no cover
        return getattr(f, '__self__', None)
    else:
        return getattr(f, 'im_self', None)

def im_class(f):
    if PY3: # pragma: no cover
        self = im_self(f)
        if self is not None:
            return self.__class__
        else:
            return None
    else:
        return getattr(f, 'im_class', None)

def with_metaclass(meta, base=object):
    """Create a base class with a metaclass."""
    return meta("NewBase", (base,), {})

if PY3: # pragma: no cover
    import builtins
    exec_ = getattr(builtins, "exec")

    def reraise(tp, value, tb=None):
        if value.__traceback__ is not tb:
            raise value.with_traceback(tb)
        raise value

else: # pragma: no cover
    def exec_(code, globs=None, locs=None):
        """Execute code in a namespace."""
        if globs is None:
            frame = sys._getframe(1)
            globs = frame.f_globals
            if locs is None:
                locs = frame.f_locals
            del frame
        elif locs is None:
            locs = globs
        exec("""exec code in globs, locs""")

    exec_("""def reraise(tp, value, tb=None):
    raise tp, value, tb
""")
