"""Genshi template loader that supports dotted names."""

from genshi.template import TemplateLoader

from tg import config


class GenshiTemplateLoader(TemplateLoader):
    """Genshi template loader supporting dotted filenames.

    Supports zipped applications and dotted filenames as well as path names.

    """

    template_extension = '.html'

    def get_dotted_filename(self, filename):
        if not filename.endswith(self.template_extension):
            finder = config['tg.app_globals'].dotted_filename_finder
            filename = finder.get_dotted_filename(
                    template_name=filename,
                    template_extension=self.template_extension)
        return filename

    def load(self, filename, relative_to=None, cls=None, encoding=None):
        """Actual loader function."""
        return TemplateLoader.load(
                self, self.get_dotted_filename(filename),
                relative_to=relative_to, cls=cls, encoding=encoding)

