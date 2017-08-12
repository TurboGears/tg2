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


try:
    from importlib import import_module
except ImportError:  # pragma: no cover
    # Compatibility module for python2.6
    import sys

    def _resolve_name(name, package, level):
        """Return the absolute name of the module to be imported."""
        if not hasattr(package, 'rindex'):
            raise ValueError("'package' not set to a string")
        dot = len(package)
        for x in xrange(level, 1, -1):
            try:
                dot = package.rindex('.', 0, dot)
            except ValueError:
                raise ValueError("attempted relative import beyond top-level "
                                 "package")
        return "%s.%s" % (package[:dot], name)

    def import_module(name, package=None):
        """Import a module.

        The 'package' argument is required when performing a relative import. It
        specifies the package to use as the anchor point from which to resolve the
        relative import to an absolute import.

        """
        if name.startswith('.'):
            if not package:
                raise TypeError("relative imports require the 'package' argument")
            level = 0
            for character in name:
                if character != '.':
                    break
                level += 1
            name = _resolve_name(name[level:], package, level)
        __import__(name)
        return sys.modules[name]