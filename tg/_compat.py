import platform, sys

if platform.system() == 'Windows': # pragma: no cover
    WIN = True
else: # pragma: no cover
    WIN = False

# True if we are running on Python 3.
PY3 = sys.version_info[0] == 3

try:
    unicode_text = unicode
except:
    unicode_text = str

if PY3:
    string_type = str
else:
    string_type = basestring
