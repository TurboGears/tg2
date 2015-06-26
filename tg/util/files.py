import os
import re
from pkg_resources import resource_filename
from .._compat import unicode_text, PY2


class DottedFileLocatorError(Exception):
    pass


class DottedFileNameFinder(object):
    """this class implements a cache system above the
    get_dotted_filename function and is designed to be stuffed
    inside the app_globals.

    It exposes a method named get_dotted_filename with the exact
    same signature as the function of the same name in this module.

    The reason is that is uses this function itself and just adds
    caching mechanism on top.
    """
    def __init__(self):
        self.__cache = dict()

    def get_dotted_filename(self, template_name, template_extension='.html'):
        """this helper function is designed to search a template or any other
        file by python module name.

        Given a string containing the file/template name passed to the @expose
        decorator we will return a resource useable as a filename even
        if the file is in fact inside a zipped egg.

        The actual implementation is a revamp of the Genshi buffet support
        plugin, but could be used with any kind a file inside a python package.

        @param template_name: the string representation of the template name
        as it has been given by the user on his @expose decorator.
        Basically this will be a string in the form of:
        "genshi:myapp.templates.somename"
        @type template_name: string

        @param template_extension: the extension we excpect the template to have,
        this MUST be the full extension as returned by the os.path.splitext
        function. This means it should contain the dot. ie: '.html'

        This argument is optional and the default value if nothing is provided will
        be '.html'
        @type template_extension: string
        """
        try:
            return self.__cache[template_name]
        except KeyError:
            # the template name was not found in our cache
            divider = template_name.rfind('.')
            if divider >= 0:
                package = template_name[:divider]
                basename = template_name[divider + 1:] + template_extension
                try:
                    result = resource_filename(package, basename)
                except ImportError as e:
                    raise DottedFileLocatorError(str(e) +". Perhaps you have forgotten an __init__.py in that folder.")
            else:
                result = template_name

            self.__cache[template_name] = result

            return result

    @classmethod
    def lookup(cls, name, extension='.html'):
        """Convenience method that permits to quickly get a file by dotted notation.

        Creates a :class:`.DottedFileNameFinder` and uses it to lookup the given file
        using dotted notation. As :class:`.DottedFileNameFinder` provides a lookup
        cache, using this method actually disables the cache as a new finder is created
        each time, for this reason if you have recurring lookups it's better to actually
        create a dotted filename finder and reuse it.

        """
        finder = cls()
        return finder.get_dotted_filename(name, extension)


_FILENAME_ASCII_STRIP_RE = re.compile(r'[^A-Za-z0-9_.-]')
_WINDOWS_DEVICE_FILES = ('CON', 'AUX', 'COM1', 'COM2', 'COM3', 'COM4', 'LPT1',
                         'LPT2', 'LPT3', 'PRN', 'NUL')

def safe_filename(filename):
    """Escapes a filename to ensure is valid and secure.

    Filename can then safely be stored on a regular file system and passed
    to :func:`os.path.join`.  The filename returned is an ASCII only string
    for maximum portability::

        >>> safe_filename("My cool movie.mov")
        'My_cool_movie.mov'
        >>> safe_filename("../../../etc/passwd")
        'etc_passwd'
        >>> safe_filename(u'i contain cool \xfcml\xe4uts.txt')
        'i_contain_cool_umlauts.txt'

    The function might return an empty filename.  .
    """
    if isinstance(filename, unicode_text):
        from unicodedata import normalize
        filename = normalize('NFKD', filename).encode('ascii', 'ignore')
        if not PY2:  # pragma: no cover
            filename = filename.decode('ascii')

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, ' ')

    filename = str(_FILENAME_ASCII_STRIP_RE.sub(
        '',
        '_'.join(filename.split())
    )).strip('._')

    # on nt a couple of special files are present in each folder.  We
    # have to ensure that the target file is not such a filename.  In
    # this case we prepend an underline
    if os.name == 'nt' and filename:  # pragma: no cover
        filebasename = filename.split('.')[0]
        if filebasename.upper() in _WINDOWS_DEVICE_FILES:
            filename = '_' + filename

    return filename
