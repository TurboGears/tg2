"""Genshi template loader that supports dotted names."""

from os.path import exists, getmtime

from jinja2.exceptions import TemplateNotFound
from jinja2.loaders import FileSystemLoader

from tg import config


class JinjaTemplateLoader(FileSystemLoader):
    """Jinja template loader supporting dotted filenames. Based on Genshi Loader

    """

    template_extension = '.html'

    def get_source(self, environment, template):

        # Check if dottedname
        if not template.endswith(self.template_extension):
            # Get the actual filename from dotted finder
            finder = config['pylons.app_globals'].dotted_filename_finder
            template = finder.get_dotted_filename(
                template_name=template,
                template_extension=self.template_extension)
        else:
            return FileSystemLoader.get_source(self, environment, template)

        # Check if the template exists
        if not exists(template):
            raise TemplateNotFound(template)

        # Get modification time
        mtime = getmtime(template)

        # Read the source
        fd = file(template)
        try:
            source = fd.read().decode('utf-8')
        finally:
            fd.close()

        return source, template, lambda: mtime == getmtime(template)

