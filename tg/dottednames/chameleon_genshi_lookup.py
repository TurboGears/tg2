"""Chameleon.Genshi template loader that supports dotted names."""

from chameleon.genshi.loader import TemplateLoader

from tg import config


class ChameleonGenshiTemplateLoader(TemplateLoader):
    """Chameleon.Genshi template loader supporting dotted filenames.

    Supports zipped applications and dotted filenames as well as path names.

    """

    template_extension = '.html'

    def get_dotted_filename(self, filename):
        if not filename.endswith(self.template_extension):
            finder = config['pylons.app_globals'].dotted_filename_finder
            filename = finder.get_dotted_filename(
                    template_name=filename,
                    template_extension=self.template_extension)
        return filename

    def load(self, filename, format='xml'):
        """Actual loader function."""
        return TemplateLoader.load(
                self, self.get_dotted_filename(filename), format)

