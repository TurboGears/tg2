"""Kajiki template loader that supports dotted names with relative paths."""

from kajiki.loader import FileLoader

from tg import config


class KajikiTemplateLoader(FileLoader):
    """Kaijik template loader supporting dotted filenames.
    Solves also the issue of not supporting relative paths when using
    py:extends in Kaijiki
    """

    template_extension = '.xml'

    def __init__(self, base, reload=True, force_mode=None):
        super(KajikiTemplateLoader, self).__init__(base, reload, force_mode)

    def _filename(self, filename):
        if not filename.endswith(self.template_extension):
            finder = config['pylons.app_globals'].dotted_filename_finder
            filename = finder.get_dotted_filename(template_name=filename,
                                                  template_extension=self.template_extension)
        return super(KajikiTemplateLoader, self)._filename(filename)
