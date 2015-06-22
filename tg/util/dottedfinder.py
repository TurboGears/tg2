from pkg_resources import resource_filename


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
