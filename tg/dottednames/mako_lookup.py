"""Reimplementation of the Mako template loader that supports dotted names."""

import os
import stat

try:
    import threading
except ImportError:
    import dummy_threading as threading


from mako.template import Template
from paste.deploy.converters import asbool

import tg


class DottedTemplateLookup(object):
    """Mako template lookup emulation that supports
    zipped applications and dotted filenames.

    This is an emulation of the Mako template lookup that will handle
    get_template and support dotted names in Python path notation
    to support zipped eggs.

    This is necessary because Mako asserts that your project will always
    be installed in a zip-unsafe manner with all files somewhere on the
    hard drive.

    This is not the case when you want your application to be deployed
    in a single zip file (zip-safe). If you want to deploy in a zip
    file _and_ use the dotted template name notation then this class
    is necessary because it emulates files on the filesystem for the
    underlying Mako engine while they are in fact in your zip file.

    """

    def __init__(self, input_encoding, output_encoding,
            imports, default_filters, module_directory=None):

        self.input_encoding = input_encoding
        self.output_encoding = output_encoding
        self.imports = imports
        self.default_filters = default_filters
        # implement a cache for the loaded templates
        self.template_cache = dict()
        # implement a cache for the filename lookups
        self.template_filenames_cache = dict()
        self.module_directory = module_directory
        self.auto_reload = asbool(tg.config.get('templating.mako.reloadfromdisk', 'false'))

        # a mutex to ensure thread safeness during template loading
        self._mutex = threading.Lock()

    def adjust_uri(self, uri, relativeto):
        """Adjust the given uri relative to a filename.

        This method is used by mako for filesystem based reasons.
        In dotted lookup land we don't adjust uri so we just return
        the value we are given without any change.

        """
        if uri.startswith('local:'):
            uri = tg.config['pylons.package'] + '.' + uri[6:]

        if '.' in uri:
            # We are in the DottedTemplateLookup system so dots in
            # names should be treated as a Python path. Since this
            # method is called by template inheritance we must
            # support dotted names also in the inheritance.
            result = tg.config['pylons.app_globals'].\
                dotted_filename_finder.get_dotted_filename(template_name=uri, template_extension='.mak')

            if not uri in self.template_filenames_cache:
                # feed our filename cache if needed.
                self.template_filenames_cache[uri] = result

        else:
            # no dot detected, just return plain name
            result = uri

        return result

    def __check(self, template):
        """private method used to verify if a template has changed
        since the last time it has been put in cache...

        This method being based on the mtime of a real file this should
        never be called on a zipped deployed application.

        This method is a ~copy/paste of the original caching system from
        the Mako lookup loader.

        """
        if template.filename is None:
            return template


        if not os.path.exists(template.filename):
            # remove from cache.
            self.template_cache.pop(template.filename, None)
            raise exceptions.TemplateLookupException(
                    "Cant locate template '%s'" % template.filename)

        elif template.module._modified_time < os.stat(
                template.filename)[stat.ST_MTIME]:

            # cache is too old, remove old template
            # from cache and reload.
            self.template_cache.pop(template.filename, None)
            return self.__load(template.filename)

        else:
            # cache is correct, use it.
            return template

    def __load(self, filename):
        """real loader function. copy paste from the mako template
        loader.

        """
        # make sure the template loading from filesystem is only done
        # one thread at a time to avoid bad clashes...
        self._mutex.acquire()
        try:
            try:
                # try returning from cache one more time in case
                # concurrent thread already loaded
                return self.template_cache[filename]

            except KeyError:
                # not in cache yet... we can continue normally
                pass

            try:
                self.template_cache[filename] = Template(
                    filename=filename,
                    module_directory=self.module_directory,
                    input_encoding=self.input_encoding,
                    output_encoding=self.output_encoding,
                    default_filters=self.default_filters,
                    imports=self.imports,
                    lookup=self)

                return self.template_cache[filename]

            except:
                self.template_cache.pop(filename, None)
                raise

        finally:
            # _always_ release the lock once done to avoid
            # "thread lock" effect
            self._mutex.release()

    def get_template(self, template_name):
        """this is the emulated method that must return a template
        instance based on a given template name
        """

        if not self.template_cache.has_key(template_name):
            # the template string is not yet loaded into the cache.
            # Do so now
            self.__load(template_name)

        if self.auto_reload:
            # AUTO RELOADING will be activated only if user has
            # explicitly asked for it in the configuration
            # return the template, but first make sure it's not outdated
            # and if outdated, refresh the cache.
            return self.__check(self.template_cache[template_name])

        else:
            return self.template_cache[template_name]

