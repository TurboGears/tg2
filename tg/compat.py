import sys

PY3 = sys.version_info[0] == 3

if PY3: # pragma: no cover
    from urllib import parse
    urlparse = parse
    from urllib.parse import quote as url_quote
    from urllib.parse import quote_plus as url_quote_plus
    from urllib.parse import unquote as url_unquote
    from urllib.parse import urlencode as url_encode
    from urllib.request import urlopen as url_open
    from urllib.request import url2pathname as url_url2pathname
    url_unquote_text = url_unquote
    url_unquote_native = url_unquote
else:
    import urlparse
    from urllib import quote as url_quote
    from urllib import quote_plus as url_quote_plus
    from urllib import unquote as url_unquote
    from urllib import urlencode as url_encode
    from urllib import url2pathname as url_url2pathname
    from urllib2 import urlopen as url_open
    def url_unquote_text(v, encoding='utf-8', errors='replace'): # pragma: no cover
        v = url_unquote(v)
        return v.decode(encoding, errors)
    def url_unquote_native(v, encoding='utf-8', errors='replace'): # pragma: no cover
        return native_(url_unquote_text(v, encoding, errors))

if PY3: # pragma: no cover
    def dict_iteritems(d):
        return d.items()
    def dict_itervalues(d):
        return d.values()
    def dict_iterkeys(d):
        return d.keys()
else:
    def dict_iteritems(d):
        return d.iteritems()
    def dict_itervalues(d):
        return d.itervalues()
    def dict_iterkeys(d):
        return d.iterkeys()