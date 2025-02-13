import importlib.resources
import os
import re
import tempfile


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

    def get_dotted_filename(self, template_name, template_extension=".html"):
        """this helper function is designed to search a template or any other
        file by python module name.

        Given a string containing the file/template name passed to the @expose
        decorator we will return a resource useable as a filename even
        if the file is in fact inside a zipped egg or in a frozen library.

        The actual implementation is a revamp of the Genshi buffet support
        plugin, but could be used with any kind a file inside a python package.

        :param template_name: the string representation of the template name
                              as it has been given by the user on his @expose decorator.
                              Basically this will be a string in the form of:
                              `"myapp.templates.somename"`
        :type template_name: str

        :param template_extension: the extension we excpect the template to have,
                                   this MUST be the full extension as returned by
                                   the os.path.splitext function.
                                   This means it should contain the dot. ie: '.html'
                                   This argument is optional and the default
                                   value if nothing is provided will be '.html'
        :type template_extension: str

        The ``template_name`` parameter also accepts a form with explicit extension
        ``myapp.templates.somename!xhtml`` that will override the ``template_exstesion``
        argument and will always use ``.xhtml`` as the extension. This is usually
        convenient in extensions and libraries that expose a template and want to
        ensure they work even in the case the application using them has a different
        extension for templates on the same engine.
        """
        cache_key = template_name
        try:
            return self.__cache[cache_key]
        except KeyError:
            # the template name was not found in our cache
            try:
                # Allow for the package.file!ext syntax
                template_name, template_extension = template_name.rsplit("!", 1)
                template_extension = "." + template_extension
            except ValueError:
                pass

            divider = template_name.rfind(".")
            if divider >= 0:
                package = template_name[:divider]
                basename = template_name[divider + 1 :]
                resourcename = basename + template_extension

                try:
                    exists = os.path.exists(importlib.import_module(package).__file__)
                    if hasattr(importlib.resources, "as_file"):
                        as_file_context = importlib.resources.as_file(
                            importlib.resources.files(package).joinpath(resourcename)
                        )
                    else:
                        # Compatibility with Python < 3.9
                        as_file_context = importlib.resources.path(
                            package, resourcename
                        )
                    with as_file_context as f:
                        if exists:
                            result = str(f)
                        else:
                            # importing from a zipfile or py2exe
                            if not hasattr(self, "__temp_dir"):
                                self.__temp_dir = tempfile.mkdtemp()

                            result = os.path.join(
                                self.__temp_dir, package, resourcename
                            )
                            if not os.path.isdir(os.path.dirname(result)):
                                os.makedirs(os.path.dirname(result))

                            with open(result, "wb") as result_f:
                                result_f.write(f.read_bytes())
                except FileNotFoundError as e:
                    # Historical behaviour has been to return file even when it doesn't exist
                    # it's up to the caller to verify that the file actually exists.
                    result = e.filename
                except ModuleNotFoundError as e:
                    raise DottedFileLocatorError(
                        "%s. Perhaps you have forgotten an __init__.py in that folder."
                        % e
                    )
            else:
                result = template_name

            result = os.path.abspath(result)
            self.__cache[cache_key] = result

            return result

    @classmethod
    def lookup(cls, name, extension=".html"):
        """Convenience method that permits to quickly get a file by dotted notation.

        Creates a :class:`.DottedFileNameFinder` and uses it to lookup the given file
        using dotted notation. As :class:`.DottedFileNameFinder` provides a lookup
        cache, using this method actually disables the cache as a new finder is created
        each time, for this reason if you have recurring lookups it's better to actually
        create a dotted filename finder and reuse it.

        """
        finder = cls()
        return finder.get_dotted_filename(name, extension)


_FILENAME_ASCII_STRIP_RE = re.compile(r"[^A-Za-z0-9_.-]")
_WINDOWS_DEVICE_FILES = (
    "CON",
    "AUX",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "LPT1",
    "LPT2",
    "LPT3",
    "PRN",
    "NUL",
)


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
    if isinstance(filename, str):
        from unicodedata import normalize

        filename = normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")

    for sep in os.path.sep, os.path.altsep:
        if sep:
            filename = filename.replace(sep, " ")

    filename = str(_FILENAME_ASCII_STRIP_RE.sub("", "_".join(filename.split()))).strip(
        "._"
    )

    # on nt a couple of special files are present in each folder.  We
    # have to ensure that the target file is not such a filename.  In
    # this case we prepend an underline
    if os.name == "nt" and filename:  # pragma: no cover
        filebasename = filename.split(".")[0]
        if filebasename.upper() in _WINDOWS_DEVICE_FILES:
            filename = "_" + filename

    return filename
